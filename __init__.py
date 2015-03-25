bl_info = {
    "name": "Intersection Free",
    "author": "Rich Colburn, Patrick Moore",
    "version": (0, 1),
    "blender": (2, 74, 0),
    "location": "View3D > Mesh > Remove Intersections",
    "description": "Tools for off-setting meshes and removing self intersections",
    "warning": "",
    "wiki_url": "",
    "category": "Edit Mesh"}


import bpy
import bmesh


def main(context):
    obj = context.active_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    print('DO SOMETHING!')
    bmesh.update_edit_mesh(me)


class MeshRemoveIntersections(bpy.types.Operator):
    """Remove Existing Self Intersections"""
    bl_idname = "mesh.remove_intersections"
    bl_label = "Remove Intersections"

    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH')

    def execute(self, context):
        main(context)
        return {'FINISHED'}

def main2(context):
    obj = context.active_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    print('DO SOMETHING!')
    bmesh.update_edit_mesh(me)
    
class IntersectionFreeOffset(bpy.types.Operator):
    """Remove Existing Self Intersections"""
    bl_idname = "object.ifree_offset"
    bl_label = "Remove Intersections"

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and context.object.type == 'MESH')

    def execute(self, context):
        main2(context)
        return {'FINISHED'}


# Registration

#def add_object_button(self, context):
#    self.layout.operator(
#        OBJECT_OT_add_object.bl_idname,
#        text="Add Object",
#        icon='PLUGIN')


# This allows you to right click on a button and link to the manual
#def add_object_manual_map():
#    url_manual_prefix = "http://wiki.blender.org/index.php/Doc:2.6/Manual/"
#    url_manual_mapping = (
#        ("bpy.ops.mesh.add_object", "Modeling/Objects"),
#        )
#    return url_manual_prefix, url_manual_mapping


def register():
    bpy.utils.register_class(IntersectionFreeOffset)
    bpy.utils.register_manual_map(MeshRemoveIntersections)
    #bpy.types.INFO_MT_mesh_add.append(add_object_button)


def unregister():
    bpy.utils.unregister_class(IntersectionFreeOffset)
    bpy.utils.unregister_manual_map(MeshRemoveIntersections)
    #bpy.types.INFO_MT_mesh_add.remove(add_object_button)

if __name__ == "__main__":
    register()
