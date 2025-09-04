# 使用
## 1. 安装 ragflow

请按照[官方文档](https://ragflow.io/docs/dev/)部署ragflow

注意点：

1. 请使用版本v0.20.4，不要用slim。此版本会自带嵌入模型。
2. 如果有GPU，请使用gpu部署命令加速推理过程。
3. 部署遇到未找到某变量问题，按提示修改`/ragflow/docker/.env`文件，打开相应变量。

## 2. 配置 ragflow

假设ragflow部署服务器ip为 `192.168.1.1`，那么变量`RAGFLOW_BASE_URL`为 `http://192.168.1.1`

如果是在本地部署，`RAGFLOW_BASE_URL`为 `http://localhost`

打开浏览器访问，注册账户，登录。

右上角点击用户头像转到profile，选择左侧菜单栏 API，申请 api_key。

左上角返回，上侧菜单选择dataset，创建项目使用的数据库。

修改项目根目录下的 `/.env` 文件，把 `RAGFLOW`开头的变量修改成刚刚获取的。账户邮箱密码可以不填，其余必填。

## 3. 运行

根据`requirements.txt`下载相关库

```shell
python .\app\app_main.py
```

记住项目运行服务器ip

## 4.客户端调用参考
