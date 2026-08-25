#### **MacroImmunet**

#### **# World**

外部世界与环境层，提供空间、field、浓度、细胞间接触等外部信息。

#### **# scanmaster**

负责从 World 中扫描与当前 Cell 相关的候选外部事件/信息。

主要考虑：

* 空间距离
* field / concentration
* 接触关系
* 时间等外部条件

ScanMaster 只负责发现候选信息，不负责判断当前 Cell 是否能够接收该信息。

#### **# inputbuilder**

负责将 ScanMaster 发现的候选外部信息转换为当前 Cell 的有效 Input。

例如：

IL2 field

&#x20;  ↓

检查 Cell 当前 receptor / label

&#x20;  ↓

有 IL2R → 转换为 IL2R-related input

无 IL2R → 无效信息

因此 InputBuilder 同时负责：外部信息 → Cell-specific input

#### **# cellmaster**

负责单个 Cell 的整体运行。

##### **## schedular**

负责决定何时以及因何原因启动计算。

主要包括：

* 外部 Input 触发
* Cell 内部状态变化触发
* 其他需要重新计算的事件

##### **## internalnet**

Cell 内部的生物学计算网络。

###### **### graph**

Graph 是 Cell 内部生物学关系的组合结构，由：

* Node
* Gene
* Behavior
* Edge

组成。

Edge 类型包括：

* Node → Node
* Node ⇄ Node
* Node → Gene
* Gene → Behavior
* Node → Behavior

edge内容包含

* 名称
* 分类
* participants
* required，决定该 Edge 对应 interaction / calculation 是否满足必要条件

Cell 持有的 Graph 由其 type / lineage position 决定，包括：

* 上阶段允许遗留的 Graph
* 当前阶段拥有的 Graph
* 下阶段允许预备的 Graph

Graph 本身采用组合制，可分为：

* 管家 Graph
* 各级共有 Graph
* 本 Type 特有 Graph

每阶段计算前，根据当前 Tick 的相关关系及其下游关系整理临时 Graph，用于辅助确定本 Tick 内的计算顺序。

###### **### lineage**

负责描述 Cell 在谱系树中的位置，以及与 lineage / type 相关的状态与转换关系。

###### **### node**

Node 是对 Cell 内物质或实体状态的抽象记录。

Node 由：

* 名称
* 分类
* total各类状态 / occupation records组成。后续计算不直接使用 Node 的 total，而是根据公式选择对应记录所占有的量。
* Formula：负责具体数值关系的计算。

###### **### passive**

Passive 是 Cell 内自动发生、无需 Cell 主动控制的生理过程。

例如：

* 物质自然衰减
* 半衰期相关变化
* 其他基础生理变化

特点：

* 无 Edge
* 无 Gate
* 具有 Formula

###### **### gene**

Gene 表示可在 Cell 内持续记录的基因状态，包括：基础状态/修饰状态/其他可记录的 Gene state，这里的 Gene 不表示 Behavior 运行过程中产生的临时“影响后值”。

* 名称
* 分类
* total各类状态 / occupation records组成。后续计算不直接使用 gene的 total，而是根据公式选择对应记录所占有的量。
* Formula：负责具体数值关系的计算。

###### **### hir**

HIR 负责从 Cell 的整体状态出发进行高层协调与参数调节。



基本流程：

AIP / modulation 接收

&#x20;       ↓

读取全局 Node

&#x20;       ↓

Node combination 激活判断

&#x20;       ↓

Lineage / Type / Graph 核实

&#x20;       ↓

Runtime Request

&#x20;       ↓

Label / State / Receptor 输出

&#x20;       ↓

State + Type interpretation

&#x20;       ↓

Parameter adjustment



HIR 不负责替代具体 Node / Gene / Behavior Formula，而是根据Type+Node combination+Cell state对 Behavior 的实际执行参数进行调节。

###### **### behavior**

Behavior 表示 Cell 中可控的生物生理过程。

Behavior Formula 表示该生理过程的意愿 / tendency而不是最终实际执行量。

Behavior 不直接使用资源、场地等 Node 作为其公式输入；这些因素属于 HIR 后续调节实际执行程度的范围。

* 名称
* 分类
* Formula：负责具体数值关系的计算。

##### **## stateupdate**

负责将 InternalNet内产生的结果整理为待提交的状态变化与 Runtime Request，包括：

* Node state change
* Node occupation / record change
* Gene state change
* Behavior 产生的状态变化
* HIR 发出的 Type / Graph 变化请求
* Cell state / label / receptor 等变化请求

StateUpdate 本身不负责最终写入 Cell，它的作用是计算结果 → 标准化的待提交变化 / Request

#### **# intentbuilder**

负责收集和整合各模块产生的请求，将其整理为统一的正式 Intent。

各类内部 request

&#x20;       ↓

IntentBuilder

&#x20;       ↓

Formal Intent

#### **# labelcenter**

作为 Cell 状态与标签的统一管理中心（SSOT）负责根据 Intent 和相关 Library：

* 查询合法定义
* 解析状态 / 标签变化
* 管理 Cell 的 Label
* 管理 receptor presentation
* 管理 Type / Graph 等相关状态
* 将最终变化交给 StateUpdate 落地

负责将计算结果和 Runtime Request 实际写回 Cell 当前状态。

