# Knowledge Extraction - Chart Shape 功能说明

## 1. 功能介绍

- 允许在图表中使用自定义形状进行数据可视化，使展示更丰富直观。

## 2. 功能行为

- 不同类型chart有不同类的shape。
- 上传自定义形状：
  - 适用图表类型：Scatter / Bubble / Point。
  - Custom Shape仅支持JPG/PNG。
  - 上传方式：支持单个/多个文件上传，也支持通过压缩包（Extract archive files）批量上传。

## 3. 上传自定义形状的管理与存储
> 本节内容仅适用于第2点所述的“上传 JPG/PNG 自定义形状”功能。

- 报表级管理：在 Edit Shape Pane 中可添加形状。
- 系统级管理：管理员可在 Enterprise Manager 中管理形状库位置:
  - Settings → Presentation → Custom Shapes
  - Settings → Content → Storage → Portal Folder
- 配置范围：支持 Global/Organization 级别配置。

## 4. 稳定性与一致性要求

- 增删改后，重启不丢失。
- 调整 Color / Size / Filter / Drill等操作后，形状显示正常。
- 导出报表（Export）时能保持 shape 的显示。

## 5.可参考的文档
- [Group Data By Dimension](https://www.inetsoft.com/docs/stylebi/InetSoftUserDocumentation/1.0.0/viewsheet/GroupDataByDimension.html#_group_by_shape)

