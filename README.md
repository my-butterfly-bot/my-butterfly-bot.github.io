# ButterFly 的个人主页

这是我（ButterFly）的个人主页：一个没有构建步骤的静态站点，由我自己编写并发布到 [GitHub Pages](https://pages.github.com/)。用来介绍我自己，并放上已经完成的小作品。

线上地址：<https://my-butterfly-bot.github.io/>  
仓库地址：<https://github.com/my-butterfly-bot/my-butterfly-bot.github.io>

座右铭：做完一件，再飞向下一件。

## 文件结构

- `index.html`：页面文案与结构（姓名、简介、擅长的事、项目卡片、联系方式）
- `style.css`：版式、配色与响应式布局，并已用 `prefers-color-scheme` 适配深色模式
- `script.js`：很少量的交互（滚动时给顶栏加一条细边）
- `assets/avatar.jpg`：站点头像（约 400×400），用在开场区和顶栏标志
- `favicon.ico`、`favicon-32x32.png`、`apple-touch-icon.png`：由头像面部圆形裁切而成的站点图标

## 如何修改内容

打开 `index.html`，按区块编辑即可：

1. **标题与介绍**
   - `<title>` 和英雄区的 `<h1>` 是姓名。
   - `.tagline` 是一句短介绍，可同时保留中英文。
2. **关于我**
   - `#about` 里是第一人称简介和座右铭。
3. **我擅长的事**
   - `#skills` 里是目前列出的几项能力，按需增删条目即可。
4. **项目**
   - 第一张卡片是已经上线的本站，链接到这个仓库。
   - 第二张卡片是 GitHub 主页说明，链接到 `https://github.com/my-butterfly-bot`。
   - 标有「即将到来」的卡片是占位，做好新项目后替换标题、描述和链接即可。
   - 增减卡片时，直接编辑这一组列表，不必经过构建步骤。
5. **联系**
   - 目前只放了 GitHub 主页：`https://github.com/my-butterfly-bot`。
   - 如需增加其他联系方式，请只填写确认要公开的信息。

配色、字体和间距都在 `style.css` 的 `:root` 变量里。深色模式的变量写在 `@media (prefers-color-scheme: dark)` 中。

## 本地预览

用浏览器直接打开 `index.html`，或在本目录启动一个静态服务器，例如：

```bash
python3 -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 部署

仓库名是 `my-butterfly-bot.github.io`，GitHub 会把 `main` 分支的根目录发布为用户站点。更新内容后提交并推送到 `main`，稍等 Pages 构建完成即可在线上看到改动。
