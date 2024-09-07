bl_info = {
    "name": "Aligning Horizontally Mini",
    "author": "KSYN",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object",
    "description": "選択したオブジェクトをグリッドに整列します",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

import bpy
import math
from collections import defaultdict

class OBJECT_OT_ArrangeObjectsInGrid(bpy.types.Operator):
    bl_idname = "object.arrange_objects_in_grid"
    bl_label = "オブジェクトをグリッドに整列"
    bl_description = "選択したオブジェクトを仮想的な立方体状に整列します"
    bl_options = {'REGISTER', 'UNDO'}

    # オペレータープロパティで分割基準文字列を指定（デフォルトはピリオド）
    split_char: bpy.props.StringProperty(name="Split Character", default=".") # type: ignore

    x_count: bpy.props.IntProperty(
        name="X軸の数",
        description="X軸に配置するオブジェクトの数",
        default=3,
        min=1
    ) # type: ignore
    
    y_count: bpy.props.IntProperty(
        name="Y軸の数",
        description="Y軸に配置するオブジェクトの数",
        default=3,
        min=1
    ) # type: ignore
    
    spacing_x: bpy.props.FloatProperty(
        name="X軸の間隔",
        description="X軸のオブジェクト間のスペース",
        default=2.0,
        min=0.1
    ) # type: ignore
    
    spacing_y: bpy.props.FloatProperty(
        name="Y軸の間隔",
        description="Y軸のオブジェクト間のスペース",
        default=2.0,
        min=0.1
    ) # type: ignore
    
    spacing_z: bpy.props.FloatProperty(
        name="Z軸の間隔",
        description="Z軸のオブジェクト間のスペース",
        default=2.0,
        min=0.1
    ) # type: ignore

    sort_active_first: bpy.props.BoolProperty(
        name="アクティブを先頭に",
        description="アクティブなオブジェクトを先頭にソートします",
        default=False
    ) # type: ignore

    pass_active: bpy.props.BoolProperty( # type: ignore
        name="Pass Active Objects",
        description="If True, active objects will be removed from groups",
        default=False
    )


    group_by_name: bpy.props.BoolProperty(
        name="名前でグループ化",
        description="オブジェクトの名前を基準にグループ化し、整列します",
        default=False
    ) # type: ignore

    group_placement_direction: bpy.props.EnumProperty(
        name="グループ配置方向",
        description="各グループを配置する方向を指定します",
        items=[
            ('X+', "X+", "X軸のプラス方向に配置"),
            ('X-', "X-", "X軸のマイナス方向に配置"),
            ('Y+', "Y+", "Y軸のプラス方向に配置"),
            ('Y-', "Y-", "Y軸のマイナス方向に配置"),
            ('Z+', "Z+", "Z軸のプラス方向に配置"),
            ('Z-', "Z-", "Z軸のマイナス方向に配置"),
        ],
        default='X+'
    ) # type: ignore
    
    group_info: bpy.props.StringProperty(
        name="グループ情報",
        description="グループの順番とオブジェクト数",
        default=""
    ) # type: ignore

    def execute(self, context):
        selected_objects = list(context.selected_objects)
        selected_objects = sorted(selected_objects, key=lambda obj: obj.name)

        active_object = context.active_object

        if not selected_objects or not active_object:
            self.report({'WARNING'}, "オブジェクトが選択されていないか、アクティブなオブジェクトがありません")
            return {'CANCELLED'}

        if self.sort_active_first:
            # アクティブオブジェクトをリストの先頭に移動
            selected_objects.remove(active_object)
            selected_objects.insert(0, active_object)

        # オブジェクトを名前でグループ化する場合
        if self.group_by_name:
            grouped_objects = self.group_objects_by_name(selected_objects)
        else:
            grouped_objects = {'All Objects': selected_objects}
        
        # グループ情報を初期化
        group_info_list = []
        
        # 初期位置
        current_position = active_object.location.copy()

        # アクティブなオブジェクトはリストから消す
        if self.pass_active:
            if active_object:
                for group_name, objects in grouped_objects.items():
                    if active_object in objects:
                        objects.remove(active_object)
        
        # グループごとに整列を行う
        for group_name, objects in grouped_objects.items():
            # 現在のグループの位置に整列
            positions = self.calculate_grid_positions(len(objects), current_position)
            for obj, pos in zip(objects, positions):
                obj.location = pos
            
            # 次のグループの初期位置を計算
            max_x, max_y, max_z = self.calculate_max_dimensions(len(objects))
            group_info_list.append(f"Group: {group_name}, Objects: {len(objects)}, Z count: {max_z}")
            
            if self.group_placement_direction == 'X+':
                current_position.x += max_x * self.spacing_x
            elif self.group_placement_direction == 'X-':
                current_position.x -= max_x * self.spacing_x
            elif self.group_placement_direction == 'Y+':
                current_position.y += max_y * self.spacing_y
            elif self.group_placement_direction == 'Y-':
                current_position.y -= max_y * self.spacing_y
            elif self.group_placement_direction == 'Z+':
                current_position.z += max_z * self.spacing_z
            elif self.group_placement_direction == 'Z-':
                current_position.z -= max_z * self.spacing_z

        # グループ情報をプロパティに格納
        self.group_info = "\n".join(group_info_list)

        self.report({'INFO'}, "オブジェクトをグリッドに整列しました")
        return {'FINISHED'}

    def calculate_grid_positions(self, total_objects, origin):
        """与えられたオブジェクト数に基づいて仮想的な立方体の点群を計算します"""
        x_count = self.x_count
        y_count = self.y_count
        
        # Z軸の個数を計算
        z_count = math.ceil(total_objects / (x_count * y_count))
        
        positions = []

        for z in range(z_count):
            for y in range(y_count):
                for x in range(x_count):
      
                    if len(positions) < total_objects:
                        if self.group_placement_direction == 'X-':
                            positions.append((
                                origin.x + -x * self.spacing_x,
                                origin.y + y * self.spacing_y,
                                origin.z + z * self.spacing_z
                            ))
                        elif self.group_placement_direction == 'Y-':
                            positions.append((
                                origin.x + x * self.spacing_x,
                                origin.y + -y * self.spacing_y,
                                origin.z + z * self.spacing_z
                            ))
                        elif self.group_placement_direction == 'Z-':
                            positions.append((
                                origin.x + x * self.spacing_x,
                                origin.y + y * self.spacing_y,
                                origin.z + -z * self.spacing_z
                            ))
                        else:
                            positions.append((
                                origin.x + x * self.spacing_x,
                                origin.y + y * self.spacing_y,
                                origin.z + z * self.spacing_z
                            ))
        return positions

    def calculate_max_dimensions(self, total_objects):
        """オブジェクト数から最大のX, Y, Zの値を計算"""
        x_count = self.x_count
        y_count = self.y_count
        
        z_count = math.ceil(total_objects / (x_count * y_count))
        
        max_x = min(total_objects, x_count)
        max_y = min(math.ceil(total_objects / x_count), y_count)
        max_z = z_count
        
        return max_x, max_y, max_z

    def group_objects_by_name(self, objects):

        """オブジェクトを名前でグループ化します"""
        groups = defaultdict(list)
        
        for obj in objects:
            # 名前の最初の部分（数字や特定の文字列まで）をグループキーとして使用
            group_key = obj.name.split(self.split_char)[0]
            groups[group_key].append(obj)
        
        return groups
    
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        
        # オペレーターのプロパティを描画

        col.prop(self, "x_count")
        col.prop(self, "y_count")
        col.prop(self, "spacing_x")
        col.prop(self, "spacing_y")
        col.prop(self, "spacing_z")
        col.prop(self, "pass_active")
        col.prop(self, "sort_active_first")
        col.prop(self, "group_by_name")
        col.prop(self, "group_placement_direction")
        col.prop(self, "split_char")
        
        # グループ情報を描画
        if self.group_info:
            col.label(text="グループ情報:")
            lines = self.group_info.splitlines()

            # 最初の10行だけ表示する
            for i, line in enumerate(lines):
                if i < 10:
                    col.label(text=line)
                else:
                    col.label(text="...省略しました")  # 10行以上の場合は説明文を表示
                    break


# クラスの登録
classes = [
    OBJECT_OT_ArrangeObjectsInGrid,
]


# オペレーターをBlenderに登録
def menu_func(self, context):
    self.layout.operator(OBJECT_OT_ArrangeObjectsInGrid.bl_idname)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
