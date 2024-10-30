import plotly.graph_objects as go
import numpy as np

def visualize(slices_input: list[str], categories: list[dict], start_at: int = 0):
    total_slices = 48  # 总共48个半小时段
    time_per_slice = 0.5  # 每个切片代表0.5小时

    # 初始化 slices 列表，长度为 48，全部填充为 'Sleeping'
    # slices = ['Sleeping'] * total_slices
    slices = ['Sleeping'] * 8 * 2 + ['Unknown'] * (total_slices - 8 * 2)

    # 计算起始索引
    start_index = int(start_at * 2) % total_slices  # 将 start_at 转换为索引

    # 将原始的 slices_input 放入正确的位置
    for i, activity in enumerate(slices_input):
        index = (start_index + i) % total_slices
        slices[index] = activity

    # 获取类别与颜色的映射
    category_colors = {cat['name']: cat.get('color', '#808080') for cat in categories}

    # 为每个切片分配颜色
    colors = [category_colors.get(activity, '#808080') for activity in slices]

    # 创建 Plotly 图表
    fig = go.Figure()

    # 添加极坐标柱状图（Barpolar）
    offset_15min = 15 / 60 / 24 * 360
    fig.add_trace(go.Barpolar(
        r=[1] * total_slices,  # 半径
        theta0=offset_15min,  # 起始角度，90度（顶部）
        dtheta=360 / total_slices,  # 每个切片的角度宽度
        marker_color=colors,
        marker_line_color='white',
        marker_line_width=0,  # 消除切片之间的缝隙
        hoverinfo='text',
        text=[
            f"{slices[i]}<br>{int(i * time_per_slice) % 24:02d}:{int((i * time_per_slice % 1) * 60):02d} - "
            f"{int((i * time_per_slice + time_per_slice) % 24):02d}:{int(((i * time_per_slice + time_per_slice) % 1) * 60):02d}"
            for i in range(total_slices)
        ],
        name='Activities',
        hoverlabel=dict(namelength=0)
    ))

    # 创建图例项
    legend_entries = []
    unique_activities = set(slices)
    for activity in unique_activities:
        color = category_colors.get(activity, '#808080')
        legend_entries.append(go.Scatterpolar(
            r=[0],
            theta=[0],
            mode='markers',
            marker=dict(color=color, size=10),
            name=activity,
            showlegend=True,
            hoverinfo='none'
        ))

    # 将图例项添加到图表中
    for entry in legend_entries:
        fig.add_trace(entry)

    # 自定义布局
    fig.update_layout(
        template=None,
        title=None,
        font_size=16,
        polar=dict(
            radialaxis=dict(range=[0, 1], showticklabels=False, ticks=''),
            angularaxis=dict(
                tickmode='array',
                tickvals=[i * (360 / 24) for i in range(24)],  # 调整刻度位置
                ticktext=[str(i) for i in range(24)],  # 刻度标签
                direction='clockwise',
                rotation=90,  # 起始位置为顶部
                dtick=15,
                showline=True,
                linewidth=1,
                gridcolor='lightgray',
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=0.9  # 将图例移动到图表右侧
        ),
        margin=dict(l=0, r=120, t=50, b=50),  # 增加右侧边距以容纳图例
    )

    # 保存图像到文件
    fig.write_image('timeslice.png', scale=2)
    # 如果您希望在浏览器中查看交互式图表，可以使用：
    # fig.show()
