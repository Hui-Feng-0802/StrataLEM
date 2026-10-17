# StrataLEM 1.2 使用说明

程序保留原来在 Python 脚本中读取 CSV/DXF、填写材料数组、创建 Slope 对象的运行方式。新增地基高度预处理是可选项，不强制使用 JSON，也不修改输入剖面。

## 先运行原有稳定性路径

1. 安装 Python 3.10 或以上版本，并安装 `requirements.txt` 中的依赖。读取 DXF 时另安装 `requirements-dxf.txt`，本机 GDAL 需支持 DXF。
2. 在 PyCharm 等编辑器中打开 `run_analysis.py`。
3. 保持 `USE_SYNTHETIC_EXAMPLE = True`、`ENABLE_FOUNDATION = False`，直接运行，即可测试合成示例。
4. 使用自己的剖面时，将 `USE_SYNTHETIC_EXAMPLE` 改为 `False`，填写 CSV/DXF 路径、DXF 实体顺序和材料数组。

材料数组每行仍为 `[黏聚力c, 内摩擦角phi, 重度gamma]`，单位依次为 kPa、度、kN/m³。各行必须与材料多边形顺序对应。DXF 仍沿用原始代码的凸包重构，应先检查是否改变了真实地层形态。

原来的构造方式继续可用：

```python
from stratalem import Slope

slp = Slope(slope_coords, strata_polys, strata_args,
            slips_num=15, slices_pieces_num=50, iterations=15)
index, circle, fs = slp.critical()
```

这三个控制量保留原代码的含义及取值截断范围。`slips_num` 是每对入口/出口的弦高样本数，不是总滑面数；`iterations` 用于确定入口/出口插值点数，不是迭代收敛次数。默认生成60条候选圆弧、划分50条土条。原脚本若采用不同搜索段，仍需显式填写 `entry_segment` 和 `exit_segment`。新程序不隐式换用其他搜索区间。

## 启用两种高度计算

将 `ENABLE_FOUNDATION` 改为 `True`。在 `FoundationInputs` 中填写原文的 e0、a、gamma1、c0、phi0、q，并填写地基分类参数。当前研究采用 q=370kPa，记为地基处采用的上覆压力，独立于待求堆高输入。

压缩变形判据默认0.20，控制高度默认按1m向下取整。地基分类保留原文的孔隙侵入厚度和底鼓临界厚度计算。beta 是该分类计算的给定坡角，应记录所用假定，不能称为程序自动求得的最优坡角。

`FoundationMaterialMap(waste_index=2, soil_index=0)` 表示材料数组第3行是排弃物料、第1行是地基土。请根据实际 DXF 顺序调整。程序核对 gamma1、c0、phi0、gamma0 的对应关系。

## 填写真实坡脚和坡顶

在 CSV 中确认两个点的索引，再填写：

```python
from stratalem import SectionReference

section_reference = SectionReference(
    toe_index=0, crest_index=-1,
    target_base=700, target_crest=840,
    elevation_offset=0, tolerance=0.05)
```

这里的0和-1只是接口示例，不能直接认作每个剖面的真实坡脚和坡顶。若为局部坐标，填写其与绝对标高的已知偏移值。程序只用偏移值核对标高，不改变稳定性计算的原始坐标。

实际高差、目标标高校核和高度约束分别输出。稳定性计算保留输入几何；指定参考点后，程序同时记录高度及Fs>1.20判据的校核结果。

## 输出和数值核对

结果保存在脚本旁的 `results` 子目录：

- `summary.json`：安全系数、临界圆弧、各阶段判定状态；
- `candidates.csv`：全部候选圆弧和对应安全系数；
- `critical_slices.csv`：临界滑面的逐条重量、底面参数、抗滑与下滑项、材料赋值回退及面积差；
- `foundation.json`：启用高度模块时的输入和计算全过程；关闭时明确写为未执行，避免同一目录遗留上次高度计算结果。

只核对两种高度公式时，直接运行 `run_foundation_only.py`，不需要提供剖面。

按文中标明参数全精度复算，Hd=140.9009009009m，Hb=152.0441597913m，采用高度仍为140m。若先采用正文给出的Nq=6.399、Nc=14.834，再计算高度，可得152.0351351351m，保留三位小数即152.035m。原文数值可以由这些中间系数复现。程序使用全精度系数，不加入匹配印刷值的校正项；相对于显示为三位小数的高度，两者相差约0.00916m。

运行全部测试：

```text
python -m unittest discover -s tests -v
```

测试检查公式实现、模式切换、数据衔接和图形导出。本版保留原圆弧筛选和条底材料回退算法。

## 自动出图

运行入口自动保存临界滑面与竖向土条图、候选滑面Fs分布图，以及启用地基模块时的极限高度对比图。
保留`slp.plot('min')`调用；支持`plot('all')`和`plot('thd',threshold=1.20)`。
`slp.save_plots('results/case')`一次保存全部计算图，格式为600dpi RGB/LZW TIFF、PNG、PDF和SVG。
详细设置及绘图工作流参考见`FIGURES.md`。

## 许可证

版权所有 (c) 2026 Hui Feng。

StrataLEM 当前版本采用 GNU 通用公共许可证第3版（仅限第3版，`GPL-3.0-only`）。
完整许可条款见 [`LICENSE`](LICENSE)。
