# A14 公开证书诊断独立静态核证

以 [A14单次诊断](A14-single-tls-certificate-diagnostic.md) 为标准，在新正式独立对话准备；作者固定交付及精确释放后，主调度另派固定raw和输出白名单。未固定前不读活动目录，不提前运行工具或网络。

只核1次声明的OpenSSL TLS握手、固定二进制/CA/命令与目标/SNI/verify_hostname、verify_return_error严格校验、已确认loopback代理/PAC/认证拒绝边界、stdin无目标HTTP、0浏览器/profile/登录/业务/回退。区别代理CONNECT和目标HTTP，不把CONNECT写成“0任何HTTP字节”。

raw stdout/stderr有TLS session秘密可能，验收只读脱敏公开证书/字段及原始长度hash，不读取未脱敏.local原文；核脱敏代码/命令未启用keylog或泄露Session-ID/Master-Key/票据。可本地解析已固定PEM，不发任何网络连接。严格区分公开SAN/链证据与未证明根因、OpenSSL与Edge信任库差别。

核精确保留Popen创建/退出/句柄/管道和额度已耗。成功也只确认该路径下本次公开证书证据；不授权新观测/忽略证书/修改代理或系统信任/登录/写入。失败只接受失败归档/释放或如实指出缺证，不补测或恢复次数。输出report.json/report.md/raw-output-manifest.json及明确限制后停止。
