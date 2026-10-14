# Edge wear for the finish: each vertex's colour says how sharp an outside edge it sits
# on, red 1 on flat or gently curved ground down to 0 on a sharp outside corner. The material wears the finish
# through to bare metal there, as handling wears a real gun's edges. Only edges turning more than 20 degrees count:
# the facets of a turned barrel or a round are no edges.
import bmesh, math

SOFT, SHARP = math.radians(20), math.radians(75)


STEP = 0.015  # m: no edge longer than 1.5 cm, so a flat face has vertices of its own, away from its edges


def edge_colors(ob):
    """Splits long edges first (a low-poly part has all its vertices on its corners: the wear would spread over
    whole faces), then colours each vertex by the sharpest outside edge it sits on. Returns how many wear."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    long_faces = [f for f in bm.faces if any(e.calc_length() > STEP for e in f.edges)]
    bmesh.ops.triangulate(bm, faces=long_faces)
    for _ in range(6):
        long_edges = [e for e in bm.edges if e.calc_length() > STEP]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me)
    bm.free()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    sharp = []
    for v in bm.verts:
        best = 0.0
        for e in v.link_edges:
            if len(e.link_faces) == 2:
                best = max(best, e.calc_face_angle_signed(0.0))  # convex edges are positive
        sharp.append(min(1.0, max(0.0, (best - SOFT) / (SHARP - SOFT))))
    bm.free()
    attr = me.color_attributes.get("Col") or me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    for i, s in enumerate(sharp):
        attr.data[i].color = (1.0 - s, 1.0 - s, 1.0 - s, 1.0)
    me.color_attributes.active_color = attr
    return sum(1 for s in sharp if s > 0.5)
