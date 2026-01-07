# 雨云自动签到工具



# 基于 Rainyun-Qiandao-V2 (Selenium) 二次开发



作者giehub ：https://github.com/SerendipityR-2022/Rainyun-Qiandao

**V2版本更新！**

**雨云签到工具 搭配计划任务可实现每日自动签到~**

众所周知，雨云为了防止白嫖加入了TCaptcha验证码，但主包对JS逆向一窍不通，纯请求的方法便走不通了。

因此只能曲线救国，使用 **Selenium+ddddocr** 来模拟真人操作。

经不严谨测试，目前的方案验证码识别率高达**48.3%**，不过多次重试最终也能通过验证，那么目的达成！



**【容器化部署指南】**

本次二次开发采用 Docker 容器化方案，实现环境隔离，杜绝宿主机环境污染。服务运行完毕后，容器将自动销毁，彻底释放服务器资源，实现零残留、零负担。

**【极简配置】**

告别繁琐的环境搭建！仅需配置几个简单的环境变量，即可一键启动，开箱即用。

**【每日自动签到】**

使用内置 Crontab 定时任务，每日自动执行脚本领取积分，无需人工干预。

**⚠️ 免责声明：** 本项目仅供技术交流与学习参考，请严格遵守相关法律法规，切勿将其用于任何商业或非法用途。







## 使用方法

### 一、宿主机方式



1. Ubuntu系统安装Python环境推荐 3.12.3 版本
2. 安装依赖以及组件等
3. 配置用户密码环境变量
4. 执行rainyun.py主程序



```
# 安装依赖信息
apt update
apt install -y git unzip wget curl gnupg locales fonts-dejavu-core libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite-dev libxdamage1 libxrandr2 libgbm1 libxss1 libasound2

# 安装Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
apt install ./google-chrome-stable_current_amd64.deb -y

version=$(google-chrome -version |awk '{print $3}') && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$version/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    git clone https://gitee.com/jd_688/Rainyun-qiandao.git

cd /Rainyun-qiandao
pip config set global.index-url https://pypi.doubanio.com/simple/
pip3 install -r requirements.txt
cp ../chromedriver-linux64/chromedriver 
chmod +x chromedriver
# 运行主程序
python3 rainyun.py
```





### 二、Docker方式 （自打包）



1. 安装Docker 已安装跳过此步骤
2. 安装git 拉取代码
3. 打包镜像
4. 运行镜像
5. 添加定时任务 (可选)



```
# 一键安装Docker
bash <(curl -sSL https://linuxmirrors.cn/docker.sh)

# 安装git
apt install -y git
git clone https://gitee.com/jd_688/Rainyun-qiandao.git
cd /Rainyun-qiandao

# 打包镜像
docker build -t rain .

# 运行镜像
docker run -d --name rain -e USER="用户名" -e PASSWORD="密码" rain 

# 查看运行日志
docker logs -f rain


# 添加定时任务 （每天8点30执行任务）
apt install cron 
(crontab -l 2>/dev/null; echo "30 8 * * * docker restart rain") | crontab -

# 查看定时任务是否添加
crontab  -l
30 8 * * * docker restart rain
```



### 三、Docker方式（使用我封装的容器）



1. 安装Docker 已安装跳过此步骤
2. 运行镜像

```
# 一键安装Docker
bash <(curl -sSL https://linuxmirrors.cn/docker.sh)

# 运行容器
docker run -d --name rain -e USER="用户名" -e PASSWORD="密码"  ccr.ccs.tencentyun.com/zqy-gitee/rainyun-qiandao

# 查看运行日志
docker logs -f rain

# 添加定时任务 （每天8点30执行任务）
apt install cron 
(crontab -l 2>/dev/null; echo "30 8 * * * docker restart rain") | crontab -

# 查看定时任务是否添加
crontab  -l
30 8 * * * docker restart rain
```





## 成功试例

![image-20260107105655708](https://oss.ziiix.cn/typora/image-20260107105655708.png)

