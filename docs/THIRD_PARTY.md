# 上游和第三方署名

## QSanguosha

项目：<https://github.com/Mogara/QSanguosha-v2>

固定提交：`e8768851bd8054db9fd1b63cd6f1feca813590d7`。

Copyright (C) 2015–2016 Mogara。保留原始 `LICENSE`、`GPLv3`、`MCFR`。上游声明 GPLv3 或后续版本，同时附有禁止商业用途的 MCFR；本交付保留这些原文，用于非商业演示，不重新授予上游素材权利。

本次修改集中在独立 GEMM 场景、原生输入/播放控制、后台记录及构建打包脚本，完整对应源码随 `SanguoshaGEMM-source.zip` 提供。原有图片、字体及卡牌资源沿用上游，未改变署名。

## Qt 5.5.1

Copyright The Qt Company Ltd. and other contributors。官方开源 MinGW 构建，动态链接使用。许可文本与 LGPL exception 位于 `licenses/qt/`，下载来源及哈希位于 `licenses/sources.json`。

版本源码：<https://download.qt.io/archive/qt/5.5/5.5.1/single/>。QtBase、QtScript、QtQuick1、QtSvg 等对应 `v5.5.1` 标签。相关第三方源码与通知随 Qt 源码提供；ANGLE 通知另附在 `licenses/qt/ANGLE-LICENSE`。

## MinGW / GCC 运行库

由上述 Qt 工具链提供 libgcc、libstdc++、winpthreads。许可、GCC Runtime Library Exception 与 MinGW-w64 通知保存在 `licenses/mingw/`。

## Lua 与 FreeType

上游内置 Lua 5.2.4，Copyright Lua.org, PUC-Rio，MIT 许可。完整原始 `lua.h`（含许可）保存在 `licenses/Lua-lua.h`，源码在 `upstream/src/lua/`。

上游使用 FreeType 2.5.5，Copyright The FreeType Project，<https://freetype.org/>。保留其 FTL/GPLv2 文本于 `licenses/freetype/`，对应源码：<https://download.savannah.gnu.org/releases/freetype/freetype-2.5.5.tar.gz>。
