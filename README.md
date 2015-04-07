# object_intersection_free
An addon for removing mesh self intersections and making offset surfaces


import bpy
import bmesh
import numpy as np
import time

current = time.time()
print('----------------start---------------')
#Properties for ui
bpy.types.Object.use_active_shape_key =  bpy.props.BoolProperty(name="Use Active Shape Key", description="Generate Surface From Acitve Shape Key", default = True)
bpy.types.Object.apply_object_modifiers =  bpy.props.BoolProperty(name="Apply Modifiers", description="Generate Surface Applied Modifers", default = False)
bpy.types.Scene.respect_boundary_edges =  bpy.props.BoolProperty(name="Respect Boundaries", description="Smooth Boundary Verts Only With Other Boundary Verts ", default = True)
bpy.types.Scene.use_selection_only =  bpy.props.BoolProperty(name="Use Selection Only", description="Work Only With Selected Vertices", default = False)
bpy.types.Scene.smooth_precision =  bpy.props.FloatProperty(name="Smooth Precision", description="For extrapolating the smoothing of collision areas", default=0.4, min=-0.9, max=0.99, soft_min=0.9, soft_max=0.99, precision=2, options={'ANIMATABLE'}, subtype='NONE', unit='NONE', update=None, get=None, set=None)
bpy.types.Scene.auto_smooth_precision =  bpy.props.BoolProperty(name="Auto Smooth Precision", description="Adjust the smoothing factor based on number of collisions", default = True)
bpy.types.Scene.offset_substeps =  bpy.props.IntProperty(name="Surface Offset Substeps", description="Divide the offsetting into small steps checking for collisions each time", default=1)
bpy.types.Scene.offset_magnitude =  bpy.props.FloatProperty(name="Offset Magnitude", description="Amount in blender units to offset surface", default=0.0)
bpy.types.Scene.use_offset_surface =  bpy.props.BoolProperty(name="Offset Surface", description="Use or do not use offset", default = False)
bpy.types.Scene.smooth_self_collisions =  bpy.props.BoolProperty(name="Smooth Self Collisions", description="Detect and smooth self collisions", default = False)


start = True
collection = 0
check_edges = set()
iterations = 0
obm = None
mode = None
edges = set()
collection_max = 0

def create_bmesh(obj):
    """For generating the bmesh with some options"""
    sce = bpy.context.scene
    if obj != None:
        if obj.type == 'MESH':
            bm = bmesh.new()
            if bpy.context.object.mode == 'OBJECT':
                if obj.apply_object_modifiers:
                    bm.from_object(obj, bpy.context.scene, apply_modifiers=True)
                elif obj.use_active_shape_key:
                    bm.from_mesh(obj.data, use_shape_key=True, shape_key_index=obj.active_shape_key_index)
                else:
                    bm.from_mesh(obj.data, use_shape_key=False)
            elif bpy.context.object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(obj.data)
    else:
        print("No active mesh")            
    bpy.context.scene.update()
    return bm

def select_link(obj_bmesh,vert):
    """Select more per vertex(not used)"""
    for ed in vert.link_edges:
        ed.select = True
    obj_bmesh.select_flush(True)

def mean_smooth(bmesh, vert):
    """Basic smoothing. Equivalent to extrapolate smooth with a factor of zero"""
    mean = np.mean(np.array([ed.other_vert(vert).co for ed in vert.link_edges]),0)
    vert.co = mean

def intersect_select(obj,bmesh_obj):
    """Check whole mesh for collisions if start is true,
       Check selection group next time,
       Selection group grows if collisions do not improve"""
    global start, collection, check_edges, edges

    # If the selection group is empty add all the edge indices to the collection
    if len(edges) == 0:    
        for ed in bmesh_obj.edges:
            edges.add(ed.index)
    # Use the copy to avoid overwrite while iterating
    check_edges = edges.copy()
    
    # Once we have the copy, clear the set if it's the first time around
    if len(edges) == len(bmesh_obj.edges):
        edges.clear()

    # Initalize the collection. The collection gets +1 for every edge collision
    collection = 0
    
    # Ensure the bmesh is up to date (This can probably be deleted to improve speed)
    bmesh_obj.edges.index_update()
    bmesh_obj.verts.index_update()
    bmesh_obj.verts.ensure_lookup_table()
    bmesh_obj.edges.ensure_lookup_table()

    # This is where the collision detection starts
    ray_cast = obj.ray_cast
    # For setting the error margin of the raycast
    EPS_NORMAL = 0.0001
    EPS_CENTER = 0.01  # should always be bigger
    current = time.time()
    for ed in check_edges:
        v1, v2 = bmesh_obj.edges[ed].verts
        
        # setup the edge with an offset
        co_1 = v1.co.copy()
        co_2 = v2.co.copy()
        co_mid = (co_1 + co_2) * 0.5
        no_mid = (v1.normal + v2.normal).normalized() * EPS_NORMAL
        co_1 = co_1.lerp(co_mid, EPS_CENTER) + no_mid
        co_2 = co_2.lerp(co_mid, EPS_CENTER) + no_mid
        co, no, index = ray_cast(co_1, co_2)
        
        # Select the collision edges
        if index != -1:
            bmesh_obj.edges[ed].select = True
            collection +=1

    bmesh_obj.select_flush(True)
    start = False

def extrapolate_smooth(bmesh, vert, value):
    """Use link_edges to determine a mean area for each vertex
       Extrapolate a position based on the direction it moves towards the mean
       Can be used to smooth more quickly or more slowly with a tradeoff in accuracy"""
    
    # When using boundary, the smoothing of boundary verts only considers other boundary verts
    if bpy.context.scene.respect_boundary_edges:
        outer = [b for b in vert.link_edges if b.is_boundary]
        if len(outer)>0:
            mean = np.mean(np.array([ed.other_vert(vert).co for ed in outer]),0)            
            extrapolate = (np.array(vert.co) - mean)*value
            vert.co = mean - extrapolate
        else:
            mean = np.mean(np.array([ed.other_vert(vert).co for ed in vert.link_edges]),0)
            extrapolate = (np.array(vert.co) - mean)*value
            vert.co = mean - extrapolate
    else:        
        mean = np.mean(np.array([ed.other_vert(vert).co for ed in vert.link_edges]),0)
        extrapolate = (np.array(vert.co) - mean)*value
        vert.co = mean - extrapolate

def deselect_all_bmesh(obj_bmesh):
    """This deselects all and possibly causes corruption of the space time continuum"""
    for v in obj_bmesh.verts:
        v.select = False
    obj_bmesh.select_flush(False)  

def select_less(obj_bmesh):
    """Use other_vert() to decrease selection area. Deselect boundary edges also"""    
    for ed in obj_bmesh.edges:
        if ed.is_boundary:
            ed.select = False
        if not ed.select:
            for v in ed.verts:
                if not v.select:
                    ed.other_vert(v).select = False
    obj_bmesh.select_flush(False)

def select_extra_bmesh(obj_bmesh):
    """Increase selection area using link edges"""
    for v in obj_bmesh.verts:
        if v.select:
            for ed in v.link_edges:
                ed.select = True
    obj_bmesh.select_flush(True)

def offset_surface(b_mesh,starting_normals,even_thickness,blend_shell,steps,factor):
    """Move vertices along their normals
       Option to blend normal with adjacent normals
       Option to use shell_factor: equivalent to "even thickness" with solidify modifier
       Option to use the starting normals every substep or recalculate each substep """
    
    if blend_shell:
        starting_normals = []
        for vert in b_mesh.verts:
            starting_normals.append(np.mean(np.array([ed.other_vert(vert).normal for ed in vert.link_edges]),0))
        if even_thickness:    
            for x in range(steps):
                for v in b_mesh.verts:
                    v.co = np.array(v.co) + (starting_normals[v.index] * v.calc_shell_factor()) * factor        
        else:
            for x in range(steps):
                for v in b_mesh.verts:
                    v.co = np.array(v.co) + starting_normals[v.index] * factor                    
    else:    
        if even_thickness:
            if starting_normals:
                starting_normals = [n.normal for n in b_mesh.verts]
                for x in range(steps):
                    for v in b_mesh.verts:
                        v.co = v.co + (starting_normals[v.index] * v.calc_shell_factor()) * factor
            else:
                for x in range(steps):
                    for v in b_mesh.verts:
                        v.co = v.co + (v.normal * v.calc_shell_factor()) * factor        
        else:
            if starting_normals:
                starting_normals = [n.normal for n in b_mesh.verts]
                for x in range(steps):
                    for v in b_mesh.verts:
                        v.co = v.co + starting_normals[v.index] * factor
            else:
                for x in range(steps):
                    for v in b_mesh.verts:
                        v.co = v.co + v.normal * factor             

def run_recursive(iters):
    """This is where we manage all the functions"""
    global start, collection, iterations, obm, mode, collection_max, edges
    if bpy.context.object != None:    
        if bpy.context.object.type == 'MESH':
            if mode != 'EDIT':    
                bpy.ops.object.mode_set(mode = 'EDIT')
            obm = create_bmesh(bpy.context.object)
            obm.verts.ensure_lookup_table()
            obm.edges.ensure_lookup_table()
            deselect_all_bmesh(obm)
            magnitude = bpy.context.scene.offset_magnitude
            
            if bpy.context.scene.use_offset_surface:
                offset_surface(obm,True,False,True,1,magnitude/iters)
                start = True
            me = bpy.data.meshes.new('proxy_data')
            proxy = bpy.data.objects.new('proxy737del', me)
            bpy.context.scene.objects.link(proxy)
            bpy.context.scene.update()

            if bpy.context.scene.smooth_self_collisions:
                """The loop here keeps running as long as the number of collision edges found is more than zero"""
                while start == True or collection>0:            
                    if collection > collection_max:
                        collection_max = collection                    
                    
                    print(collection, 'collisions remaining')
                    last_time = collection                
                    obm.to_mesh(me)
                    bpy.context.scene.update()
                    intersect_select(proxy,obm)    

                    if collection >= last_time:
                        iterations += 1

                    elif collection < last_time:
                        edges.clear()
                        deselect_all_bmesh(obm)
                        iterations = 0 
                        
                    if iterations > 0:    
                        for x in range(iterations):
                            select_extra_bmesh(obm)
                        
                    if bpy.context.scene.auto_smooth_precision:
                        if collection_max == 0:
                            factor = 0.3
                        else:
                            factor = collection *(0.4/collection_max) 
                    else:
                        factor = bpy.context.scene.smooth_precision
                    for iter in range(2):
                        for v in obm.verts:
                            if v.select:
                                extrapolate_smooth(obm, v, factor)

                    for eddy in obm.edges:
                        if eddy.select:
                            edges.add(eddy.index)
                    
                    deselect_all_bmesh(obm)

            obm.free()
    
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob in bpy.context.scene.objects:
        ob.select = ob.type == 'MESH' and ob.name.startswith("proxy737del")
    bpy.ops.object.delete()


def offset_surface_function():
    """This enables collision smoothing to run each substep of the surface offset"""
    mode = bpy.context.object.mode    
    iters = bpy.context.scene.offset_substeps
    for x in range(iters):
        run_recursive(iters)     
    bpy.ops.object.mode_set(mode=mode)           


# Test call:    
offset_surface_function()    


print('total time: ',time.time()-current)

"""With default bmesh setting, it's effective to run this whith an active shape key
   This allows you to quickly compare the original mesh to the offset mesh by turning the key on and off"""




# Consider option for external collision object. Might make for some interesting effect with a frame handler (like clay)
# Consider checking if the points are moving to determine whether or not to select extra
# Consider modifying the smooth function to operate on a copy of coords to avoid ripples
