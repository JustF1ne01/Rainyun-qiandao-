FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.12.3-slim
ENV TZ=Asia/Shanghai
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/*

RUN apt update && apt install -y git unzip wget curl gnupg locales fonts-dejavu-core libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite-dev libxdamage1 libxrandr2 libgbm1 libxss1 libasound2 && \
    # 设置中文locale
    echo "zh_CN.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    # 安装Chrome
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install ./google-chrome-stable_current_amd64.deb -y && \
    rm -rf /var/lib/apt/lists/* ./google-chrome-stable_current_amd64.deb

RUN version=$(google-chrome -version |awk '{print $3}') && \
    wget https://storage.googleapis.com/chrome-for-testing-public/$version/linux64/chromedriver-linux64.zip && \
    unzip chromedriver-linux64.zip && \
    git clone https://gitee.com/jd_688/Rainyun-qiandao.git

WORKDIR /Rainyun-qiandao
RUN pip config set global.index-url https://pypi.doubanio.com/simple/ && \
    pip3 install -r requirements.txt && \
    cp ../chromedriver-linux64/chromedriver  ./ && \
    rm -rf ../chromedriver-linux64  ../chromedriver-linux64.zip && \
    chmod +x chromedriver

CMD ["python3", "rainyun.py"]
