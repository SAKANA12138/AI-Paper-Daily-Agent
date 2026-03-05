# 💎 Elite AI Paper Daily Bot 
**基于 Gemini 2.5 Flash 与 GitHub Actions 的“无服务器 (Serverless)”学术论文追踪智能体**

这是一个高度自动化的 AI 论文筛选与解剖系统。它每天会自动从全网海量论文中，筛选出你最关心的领域的**顶级会议/高影响力论文**，并利用大语言模型（LLM）进行深度剖析，最后以精美的 Markdown 格式推送到你的手机（通过 GitHub Issues）。

## ✨ 核心特性

- 🎯 **双阶段精英检索**：优先锁定顶会（NeurIPS, ICLR, CVPR 等），数量不足时自动扩展至全网高引用论文。
- 🧠 **AI 深度解剖 (Agentic)**：不仅是翻译摘要，而是利用 Gemini 从“范式转移”、“底层第一性原理”、“工程落地难度”等维度对论文进行严苛审视。
- 自动化记忆机制：自动维护 `elite_processed_ids.txt` 历史记录，确保每天推送的都是**绝对全新**的内容。
- ☁️ **零成本无服务器部署**：完全依托 GitHub Actions 定时运行，无需购买任何云服务器。
- 📱 **移动端优雅推送**：利用 GitHub Issue 自动生成日报，手机端随时随地“像刷朋友圈一样”读论文。

## 🚀 快速开始 (仅需 3 分钟)

想要拥有你自己的专属学术 AI 助手？按照以下步骤操作：

1. **Fork 本仓库**：点击右上角的 `Fork` 按钮，将项目复制到你的账号下。
2. **获取 API Key**：前往 [Google AI Studio](https://aistudio.google.com/) 免费获取一个 Gemini API Key。
3. **配置 GitHub Secrets**：
   - 进入你 Fork 后的仓库 -> `Settings` -> `Secrets and variables` -> `Actions`。
   - 点击 `New repository secret`。
   - Name 填入：`GOOGLE_API_KEY`，Value 填入你的 API Key。
4. **授予读写权限**（关键）：
   - 进入 `Settings` -> `Actions` -> `General`。
   - 滑动到最下方，将 `Workflow permissions` 修改为 **Read and write permissions** 并保存。
5. **修改你的追踪领域**：
   - 打开 `main.py`，将最下方的 `TOPIC = "LLM Agents planning reasoning"` 修改为你自己感兴趣的研究方向。
6. **启用 Actions**：
   - 点击仓库顶部的 `Actions` 标签页，点击 `I understand my workflows, go ahead and enable them`。
   - 在左侧点击 `💎 Elite Paper Daily Bot`，然后点击 `Run workflow` 进行首次手动测试！

## 🛠️ 技术栈

- **数据源**: [Semantic Scholar Graph API](https://www.semanticscholar.org/product/api)
- **大模型**: Google Gemini 2.5 Flash (via `langchain-google-genai`)
- **自动化流**: GitHub Actions CI/CD

## 🤝 贡献与反馈

欢迎提交 Pull Request 来完善这个项目，或者通过 Issue 提出你宝贵的建议！
