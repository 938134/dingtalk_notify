# 钉钉消息机器人 (DingTalk Notify) Home Assistant 集成

[![GitHub Release](https://img.shields.io/github/release/938134/dingtalk_notify.svg)](https://github.com/938134/dingtalk_notify/releases)
[![License](https://img.shields.io/github/license/938134/dingtalk_notify.svg)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

这是一个 Home Assistant 自定义集成，允许您通过钉钉群机器人发送通知消息。

## 功能特点

- 🔐 **安全认证**：支持 Token 和 Secret 签名认证
- 📱 **多种消息类型**：支持文本、Markdown、链接、互动卡片
- ⚡ **高性能**：异步处理，请求重试机制
- 🔧 **易于配置**：通过 UI 配置界面轻松设置
- 🎯 **稳定可靠**：自动重试失败请求

## 安装

### 方法一：HACS 安装（推荐）

1. 在 HACS 中，点击「集成」
2. 点击右上角三个点，选择「自定义仓库」
3. 添加仓库：`https://github.com/938134/dingtalk_notify`
4. 分类选择「集成」
5. 在集成列表中搜索「钉钉消息机器人」并安装

### 方法二：手动安装

1. 下载 `dingtalk_notify` 文件夹
2. 将其复制到 Home Assistant 的 `custom_components` 目录
3. 重启 Home Assistant

## 配置

### 步骤 1：创建钉钉群机器人

1. 在钉钉群中，点击右上角设置图标
2. 选择「智能群助手」
3. 点击「添加机器人」
4. 选择「自定义」机器人
5. 设置机器人名称和安全设置（建议使用「加签」）
6. 记录 Webhook 地址中的 `access_token` 和加签密钥

### 步骤 2：在 Home Assistant 中配置

1. 进入 Home Assistant 的「配置」->「集成」
2. 点击「添加集成」
3. 搜索「钉钉消息机器人」
4. 填写以下信息：
   - **Token**: 机器人的 access_token
   - **Secret**: 机器人的加签密钥（如果设置了加签）

## 使用方法

### 通过服务调用发送消息

集成安装后，会自动创建一个通知服务 `notify.dingtalk_notify`。

**基本文本消息：**
```yaml
service: notify.dingtalk_notify
data:
  message: "这是一条测试消息"
  title: "Home Assistant 通知"
```

**Markdown 消息：**
```yaml
service: notify.dingtalk_notify
data:
  message: "### 温度警报\n- 位置: 客厅\n- 当前温度: 25°C\n- 状态: **正常**"
  title: "环境监测"
  data:
    message_type: "markdown"
```

**链接消息：**
```yaml
service: notify.dingtalk_notify
data:
  message: "点击查看 Home Assistant 控制面板"
  title: "快速访问"
  data:
    message_type: "link"
    link_url: "https://your-ha-url.com"
    link_pic_url: "https://example.com/image.jpg"
```

**互动卡片消息：**
```yaml
service: notify.dingtalk_notify
data:
  message: "### 设备控制\n请选择操作"
  title: "智能家居控制"
  data:
    message_type: "actionCard"
    button_orientation: "0"  # 0-垂直，1-水平
    buttons:
      - title: "打开灯光"
        action_url: "https://your-service-url.com/turn_on"
      - title: "关闭灯光" 
        action_url: "https://your-service-url.com/turn_off"
```

## 服务数据参数

### 通用参数
- `message` (必需): 消息内容
- `title`: 消息标题
- `data`: 附加数据

### data 参数
- `message_type`: 消息类型，可选值：`text`, `markdown`, `link`, `actionCard`
- `link_url`: 链接消息的目标 URL（仅 link 类型）
- `link_pic_url`: 链接消息的图片 URL（仅 link 类型）
- `button_orientation`: 按钮排列方向，0-垂直，1-水平（仅 actionCard 类型）
- `buttons`: 按钮列表（仅 actionCard 类型）

## 自动化示例

```yaml
alias: "温度过高通知"
trigger:
  - platform: numeric_state
    entity_id: sensor.temperature
    above: 30
action:
  - service: notify.dingtalk_notify
    data:
      title: "⚠️ 温度警报"
      message: "### 温度过高警告\n- 位置: 客厅\n- 当前温度: {{ states('sensor.temperature') }}°C\n- 建议: 请检查空调状态"
      data:
        message_type: markdown
```

## 故障排除

### 常见问题

1. **消息发送失败**
   - 检查 Token 和 Secret 是否正确
   - 确认网络连接正常
   - 查看 Home Assistant 日志获取详细错误信息

2. **集成无法添加**
   - 确认已正确安装集成
   - 重启 Home Assistant 后重试

### 日志调试

在 `configuration.yaml` 中添加以下配置启用调试日志：

```yaml
logger:
  default: info
  logs:
    custom_components.dingtalk_notify: debug
```

## 支持与反馈

如果您遇到问题或有建议，请通过以下方式联系：

- [GitHub Issues](https://github.com/938134/dingtalk_notify/issues)
- 功能请求和 Bug 报告

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 更新日志

### v1.1.0
- 添加配置选项支持
- 优化错误处理机制
- 改进用户体验

---

**注意**: 此集成非官方钉钉产品，由社区开发和维护。