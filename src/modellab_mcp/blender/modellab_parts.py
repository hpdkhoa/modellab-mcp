"""Model Lab's shapes, in Blender. Every shape is built in gun space, as every rig here:
cm, +X the gun's left, +Y forward along the bore, +Z up. Blender's world is metres with Y flipped (the FBX importer
flips it back), so g() turns gun cm into Blender metres. Each shape belongs to one bone (one moving part) and one
material slot; Kit.rig() joins them into one skinned mesh, every vertex on its part's bone alone."""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def g(x, y, z):
    """Gun space (cm) to Blender world (m)."""
    return Vector((x, -y, z)) / 100.0


def ug(v):
    """Blender world (m) to gun space (cm)."""
    return Vector((v.x * 100.0, -v.y * 100.0, v.z * 100.0))


def _active(ob):
    for o in bpy.context.scene.objects:   # the scene's own list: a removed cutter leaves no stale entry here
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    _active(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def _smooth_sides(ob, axis):
    """A cylinder's sides shaded smooth, its flat ends left flat (axis in Blender's frame)."""
    for f in ob.data.polygons:
        f.use_smooth = abs(f.normal.dot(axis)) < 0.5


def rounded(pts, r, segs=3):
    """A 2D polygon with each corner rounded (radius r, kept to half of the shorter side)."""
    if r <= 0:
        return list(pts)
    out = []
    n = len(pts)
    for i in range(n):
        a, p, b = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        da, db = (a - p), (b - p)
        rr = min(r, da.length / 2, db.length / 2)
        s0, s1 = p + da.normalized() * rr, p + db.normalized() * rr
        for k in range(segs + 1):
            t = k / segs
            q = s0 * (1 - t) ** 2 + p * 2 * (1 - t) * t + s1 * t * t   # a quadratic curve through the corner
            out.append((q.x, q.y))
    return out


def ring(center, u, v, a, b, n=16, p=2.0, start=0.0):
    """n points round center (gun cm): a along u, b along v; p 2 an ellipse, larger p squarer (a rounded box)."""
    c, u, v = Vector(center), Vector(u).normalized(), Vector(v).normalized()
    pts = []
    for k in range(n):
        t = start + 2 * math.pi * k / n
        ct, st = math.cos(t), math.sin(t)
        x = math.copysign(abs(ct) ** (2.0 / p), ct)
        y = math.copysign(abs(st) ** (2.0 / p), st)
        pts.append(c + u * a * x + v * b * y)
    return pts


def _sock(sockets, ident):
    for x in sockets:
        if x.identifier == ident:
            return x
    return None


def material(name, color, metal, rough, wear=None):
    """A material for the pictures and the FBX: the finish's colour, metalness and roughness. wear: the bare metal's
    colour, shown on sharp outside edges through the vertex colour Col (finish_util: red 1 flat, 0 a sharp edge)."""
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)        # Workbench and the viewport
    m.metallic = metal
    m.roughness = rough
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if wear:
        col = nt.nodes.new("ShaderNodeVertexColor")
        col.layer_name = "Col"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        band = nt.nodes.new("ShaderNodeMapRange")             # only the sharpest edges wear, and never to bare metal
        band.clamp = True
        band.inputs["From Min"].default_value = 0.7
        band.inputs["From Max"].default_value = 1.0
        band.inputs["To Min"].default_value = 0.0
        band.inputs["To Max"].default_value = 0.6
        nt.links.new(col.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[0], inv.inputs[1])            # the edge's sharpness: 1 - red
        nt.links.new(inv.outputs[0], band.inputs["Value"])
        nt.links.new(band.outputs[0], _sock(mix.inputs, "Factor_Float"))
        _sock(mix.inputs, "A_Color").default_value = (*color, 1.0)
        _sock(mix.inputs, "B_Color").default_value = (*wear, 1.0)
        nt.links.new(_sock(mix.outputs, "Result_Color"), bsdf.inputs["Base Color"])
        shine = nt.nodes.new("ShaderNodeMath")                  # worn edges are a little shinier
        shine.operation = 'MULTIPLY_ADD'
        nt.links.new(band.outputs[0], shine.inputs[0])
        shine.inputs[1].default_value = -0.25
        shine.inputs[2].default_value = rough
        nt.links.new(shine.outputs[0], bsdf.inputs["Roughness"])
    return m


def _see_through(m, alpha):
    """Glass in the pictures: mostly clear, blended over what lies behind it. The game gives the slot its own glass."""
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Alpha"].default_value = alpha
    for attr, val in (("surface_render_method", 'BLENDED'), ("blend_method", 'BLEND')):
        try:
            setattr(m, attr, val)
        except (AttributeError, TypeError):
            pass
    m.diffuse_color = (*m.diffuse_color[:3], alpha)


class Kit:
    def __init__(self, materials):
        """materials: {slot name: (r, g, b) or ((r, g, b), metallic, roughness)}; a game sets its own finish by slot;
        the colours here are the build's own and show in its pictures."""
        self.mats = {}
        for name, spec in materials.items():
            color, metal, rough = (spec, 0.2, 0.5) if isinstance(spec[0], (int, float)) else spec[:3]
            wear = spec[3] if not isinstance(spec[0], (int, float)) and len(spec) > 3 else None
            self.mats[name] = material(name, color, metal, rough, wear)
            if not isinstance(spec[0], (int, float)) and len(spec) > 4:   # glass: the pictures see through it
                _see_through(self.mats[name], spec[4])
        self.parts = {}       # bone -> [objects]
        self.named = {}       # shape name -> object (for measuring)

    @classmethod
    def like(cls, other):
        """A new kit on another's materials: an attachment, drawn and rigged apart from the gun."""
        k = cls.__new__(cls)
        k.mats, k.parts, k.named = other.mats, {}, {}
        return k

    # --- shapes -------------------------------------------------------------------------------------------------
    def _keep(self, ob, name, mat, bone, bevel):
        ob.name = name
        ob.data.materials.clear()
        ob.data.materials.append(self.mats[mat])
        if bevel > 0:
            b = ob.modifiers.new("bevel", 'BEVEL')
            b.width = bevel / 100.0
            b.segments = 2
            b.limit_method = 'ANGLE'
            b.angle_limit = math.radians(35)
            b.harden_normals = False
        apply_mods(ob)
        self.parts.setdefault(bone, []).append(ob)
        self.named[name] = ob
        return ob

    def prism(self, name, pts, axis, a0, a1, mat, bone, bevel=0.08, round_r=0.0, smooth=False):
        """A polygon extruded straight. axis 'x': pts are (y, z), from x a0 to a1 (a side profile); axis 'y': pts are
        (x, z), from y a0 to a1 (a front profile); axis 'z': pts are (x, y), from z a0 to a1 (a top profile)."""
        def at(p, a):
            if axis == 'x':
                return g(a, p[0], p[1])
            if axis == 'y':
                return g(p[0], a, p[1])
            return g(p[0], p[1], a)
        pts = rounded(pts, round_r)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        lo = [bm.verts.new(at(p, a0)) for p in pts]
        hi = [bm.verts.new(at(p, a1)) for p in pts]
        bm.faces.new(lo)
        bm.faces.new(list(reversed(hi)))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        if smooth:
            for f in me.polygons:
                f.use_smooth = True
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return self._keep(ob, name, mat, bone, bevel)

    def loft(self, name, rings, mat, bone, caps=(True, True), smooth=True, closed=False, subdiv=0):
        """A smooth shape through rings of points (gun cm, the same count each): a grip, a stock, a sleeve."""
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        rv = [[bm.verts.new(g(*p)) for p in r] for r in rings]
        n = len(rings[0])
        pairs = list(zip(rv, rv[1:])) + ([(rv[-1], rv[0])] if closed else [])
        for r0, r1 in pairs:
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
        if not closed:
            if caps[0]:
                bm.faces.new(list(reversed(rv[0])))
            if caps[1]:
                bm.faces.new(rv[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        if smooth:
            for f in me.polygons:
                f.use_smooth = True
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if subdiv:
            s = ob.modifiers.new("smooth", 'SUBSURF')
            s.levels = subdiv
            s.render_levels = subdiv
        return self._keep(ob, name, mat, bone, 0.0)

    def sweep(self, name, path, a, b, mat, bone, n=10, p=2.0, up=(0, 0, 1), closed=False, smooth=True):
        """A section (a across, b in the path's plane) swept along a path of gun points: the trigger guard, a rib."""
        path = [Vector(q) for q in path]
        rings = []
        for i, q in enumerate(path):
            t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            u = Vector(up).cross(t)
            if u.length < 1e-6:
                u = Vector((1, 0, 0)).cross(t)
            u.normalize()
            v = t.cross(u).normalized()
            rings.append(ring(q, u, v, a, b, n, p))
        return self.loft(name, rings, mat, bone, smooth=smooth, closed=closed)

    def rod(self, name, p0, p1, r0, r1=None, mat="Steel", bone="Root", n=12, caps=(True, True), smooth=True):
        """A cylinder or cone between two gun points, any direction."""
        r1 = r0 if r1 is None else r1
        a, b = Vector(p0), Vector(p1)
        t = (b - a).normalized()
        u = Vector((0, 0, 1)).cross(t)
        if u.length < 1e-6:
            u = Vector((1, 0, 0)).cross(t)
        u.normalize()
        v = t.cross(u)
        return self.loft(name, [ring(a, u, v, r0, r0, n), ring(b, u, v, r1, r1, n)], mat, bone, caps=caps, smooth=smooth)

    def box(self, name, lo, hi, mat, bone, bevel=0.08):
        """An axis-aligned box from lo to hi (gun cm)."""
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        return self.prism(name, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], 'x', x0, x1, mat, bone, bevel)

    def tube(self, name, y0, y1, r0, r1=None, x=0.0, z=0.0, mat="Metal", bone="Root", verts=24, bevel=0.0):
        """A cylinder or cone along the gun's Y, radius r0 at y0 and r1 at y1."""
        r1 = r0 if r1 is None else r1
        if y1 < y0:   # drawn backward: the same tube from its front end
            y0, y1, r0, r1 = y1, y0, r1, r0
        # the cone's radius2 end turns to gun +Y (Blender -Y) with this rotation
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0 / 100, radius2=r1 / 100, depth=(y1 - y0) / 100,
                                        location=g(x, (y0 + y1) / 2, z), rotation=(math.pi / 2, 0, 0))
        ob = bpy.context.object
        _active(ob)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        _smooth_sides(ob, Vector((0, 1, 0)))
        return self._keep(ob, name, mat, bone, bevel)

    def tube_x(self, name, x0, x1, r, y, z, mat="Metal", bone="Root", verts=16):
        """A short cylinder across the gun (along X): pins, knobs, buttons."""
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r / 100, depth=abs(x1 - x0) / 100,
                                            location=g((x0 + x1) / 2, y, z), rotation=(0, math.pi / 2, 0))
        ob = bpy.context.object
        _active(ob)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        _smooth_sides(ob, Vector((1, 0, 0)))
        return self._keep(ob, name, mat, bone, 0.0)

    def cut(self, ob, lo, hi, cutter=None):
        """Takes an axis-aligned box (gun cm), or a cutter shape, out of a shape: the port, the well's hole, slots."""
        cutter = cutter or self.box("_cutter", lo, hi, list(self.mats)[0], "_cut", bevel=0.0)
        for obs in self.parts.values():
            if cutter in obs:
                obs.remove(cutter)
        self.named = {k: v for k, v in self.named.items() if v is not cutter}
        m = ob.modifiers.new("cut", 'BOOLEAN')
        m.operation = 'DIFFERENCE'
        m.object = cutter
        m.solver = 'EXACT'
        apply_mods(ob)
        bpy.data.objects.remove(cutter, do_unlink=True)
        return ob

    # --- surface texture ------------------------------------------------------------------------------------------
    def texture(self, name, on, origin, a, b, half_a, half_b, side, kind="checkered", pitch=0.3, depth=0.06,
                mat=None, bone="Root", seed=1):
        """A gripping texture laid on a shape's side (gun cm): checkering (a diamond pyramid lattice) or stipple
        (random bumps). origin, a and b span the panel (a, b unit directions in the side's plane, half_a, half_b its
        rounded-rectangle half sizes); side is the direction the panel faces (+1 the gun's left, -1 its right).
        Each lattice point is cast onto the shape, then raised along the surface normal: real geometry, so the
        texture shows in the game too, not only in these pictures."""
        dg = bpy.context.evaluated_depsgraph_get()
        tree = BVHTree.FromObject(on, dg)
        o = Vector(origin)
        ea, eb = Vector(a).normalized(), Vector(b).normalized()   # the panel's own axes: its rounded outline
        if kind == "checkered":                    # the checkering lines run at 45 degrees to the panel's edges
            pa, pb, step = (ea + eb).normalized(), (ea - eb).normalized(), pitch / 2.0
        else:
            pa, pb, step = ea, eb, pitch
        n = int(math.hypot(half_a, half_b) / step) + 1
        rnd = random.Random(seed)
        out = Vector((side, 0.0, 0.0))
        bm = bmesh.new()
        grid = {}
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                q = o + pa * (i * step) + pb * (j * step)
                d = q - o
                u, v = d.dot(ea) / half_a, d.dot(eb) / half_b
                if u ** 4 + v ** 4 > 1.0:
                    continue
                start = g(*(q + out * 6.0))
                hit, normal, _, _ = tree.ray_cast(start, Vector((-side, 0.0, 0.0)))
                if hit is None:
                    continue
                if kind == "checkered":
                    h = depth if (i % 2 and j % 2) else 0.0
                else:
                    h = depth * rnd.random() ** 0.7
                fade = min(1.0, (1.0 - (u ** 4 + v ** 4)) * 6.0)   # the texture runs out at its edge
                grid[(i, j)] = bm.verts.new(hit + normal * ((0.004 + h * fade) / 100.0))
        for (i, j), v00 in grid.items():
            k = [grid.get(c) for c in ((i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if all(k):
                quad = [v00, k[0], k[1], k[2]]
                if kind != "checkered" or (i % 2) == (j % 2):   # split through the pyramid's apex
                    bm.faces.new((quad[0], quad[1], quad[2]))
                    bm.faces.new((quad[0], quad[2], quad[3]))
                else:
                    bm.faces.new((quad[1], quad[2], quad[3]))
                    bm.faces.new((quad[1], quad[3], quad[0]))
        bm.normal_update()
        for f in bm.faces:                        # every face looks out of the shape
            if f.normal.x * side < 0:
                f.normal_flip()
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        for f in me.polygons:
            f.use_smooth = kind != "checkered"
        return self._keep(ob, name, mat or on.data.materials[0].name, bone, 0.0)

    # --- measuring ------------------------------------------------------------------------------------------------
    def bounds(self, *names):
        """The gun-space box (lo, hi) of named shapes as they stand now."""
        pts = []
        for n in names:
            ob = self.named[n]
            pts += [ug(ob.matrix_world @ v.co) for v in ob.data.vertices]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        return lo, hi

    def bone_bounds(self, bone):
        return self.bounds(*[o.name for o in self.parts.get(bone, [])])

    # --- the rig --------------------------------------------------------------------------------------------------
    def refine_slots(self, rule=None):
        """Material slots made finer by the platform's rule (rule(shape name, slot) -> slot): the upper and the lower
        of one receiver, the barrel apart from the bolt, so a coating can give each its own finish. Returns
        {slot: [shape names]}, every shape that will be in the rig."""
        out = {}
        for obs in self.parts.values():
            for ob in obs:
                if not ob.data.materials:
                    continue
                base = ob.name.split(".")[0]
                slot = ob.data.materials[0].name
                new = rule(base, slot) if rule else slot
                if new != slot and new in self.mats:
                    ob.data.materials[0] = self.mats[new]
                    slot = new
                out.setdefault(slot, []).append(base)
        return {k: sorted(set(v)) for k, v in sorted(out.items())}

    def rig(self, name, bones, edge_colors=None):
        """One mesh on an armature. bones: [(bone, head in gun cm, parent or None)]; a bone points back along the gun
        (Blender +Y), as the hand-made rigs do. Every vertex goes on its part's bone alone. Returns (armature, mesh)."""
        for bone, obs in self.parts.items():
            for ob in obs:
                ob.data.transform(ob.matrix_world)
                ob.matrix_world = Matrix.Identity(4)
                vg = ob.vertex_groups.new(name=bone)
                vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
        every = [ob for obs in self.parts.values() for ob in obs]
        for o in bpy.context.scene.objects:
            o.select_set(False)
        for ob in every:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = every[0]
        bpy.ops.object.join()
        mesh = bpy.context.object
        mesh.name = name + "_Mesh"
        if edge_colors:
            edge_colors(mesh)
        arm_data = bpy.data.armatures.new("SKEL_" + name)
        arm = bpy.data.objects.new(name, arm_data)
        bpy.context.scene.collection.objects.link(arm)
        _active(arm)
        bpy.ops.object.mode_set(mode='EDIT')
        for bone, head, parent in bones:
            b = arm_data.edit_bones.new(bone)
            b.head = g(*head)
            b.tail = b.head + Vector((0, 0.02, 0))
            if parent:
                b.parent = arm_data.edit_bones[parent]
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.parent = arm
        mesh.modifiers.new("Armature", 'ARMATURE').object = arm
        return arm, mesh
