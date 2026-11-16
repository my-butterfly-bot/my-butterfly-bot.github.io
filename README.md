# Rainy Summer 的个人主页

这是一个面向 [GitHub Pages](https://pages.github.com/) 的静态个人主页模板，属于 GitHub 账号 [my-butterfly-bot](https://github.com/my-butterfly-bot)，内容以 Rainy Summer 为主人公。站点没有构建步骤，把文件推到 `main` 分支即可发布。

线上地址：<https://my-butterfly-bot.github.io/>

## 文件结构

- `index.html`：页面文案与结构（姓名、简介、项目卡片、联系方式）
- `style.css`：版式、配色与响应式布局，并已用 `prefers-color-scheme` 适配深色模式
- `script.js`：很少量的交互（滚动时给顶栏加一条细边）

## 如何修改内容

打开 `index.html`，按区块替换即可：

1. **标题与介绍**
   - `<title>` 和英雄区的 `<h1>` 是姓名。
   - `.tagline` 是一句短介绍，可同时保留中英文。
2. **关于**
   - `#about` 里的标题和两段文字，换成真实简介。
3. **项目**
   - `#projects` 里标有「项目示例」的三张卡片是占位内容。
   - 改标题和描述，或把整张卡片复制、删除来增减项目。
   - 若要加上链接，可把标题包进 `<a href="...">`，或在卡片底部增加一个链接。
4. **联系**
   - 目前只放了 GitHub 主页：`https://github.com/my-butterfly-bot`。
   - 如需增加其他联系方式，请只填写你确认要公开的信息。

配色、字体和间距都在 `style.css` 的 `:root` 变量里。深色模式的变量写在 `@media (prefers-color-scheme: dark)` 中。

## 本地预览

用浏览器直接打开 `index.html`，或在本目录启动一个静态服务器，例如：

```bash
python3 -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 部署

仓库名是 `my-butterfly-bot.github.io`，GitHub 会把 `main` 分支的根目录发布为用户站点。更新内容后提交并推送到 `main`，稍等 Pages 构建完成即可在线上看到改动。
