## 超对称数据
超对称数据

### 使用说明
使用说明

```python
from jqdata import ssymmetry
df=ssymmetry.run_query(query(ssymmetry.ecommerce_data).filter(ssymmetry.ecommerce_data.date =='2019-04-14').limit(n))

```

获取超对称数据，包含股吧、雪球情绪指数和淘宝、天猫电商销量数据
参数：

- query(ssymmetry.ecommerce_data)：表示从ssymmetry.ecommerce_data 这张表中查询电商数据，其中ssymmetry是库名，ecommerce_data是表名。ssymmetry库中共有5张表，都可以使用run_query方法调用，表名如下所示：

表名
描述
起始时间
更新频率

guba_sentiment_daily
股吧天度情绪指数
2007.01.03
T日凌晨4:00更新T-2日数据

guba_sentiment_hourly
股吧小时情绪指数
2018.08.02
T日凌晨4:00更新T-2日数据

xueqiu_sentiment_daily
雪球天度情绪指数
2011.10.27
T日凌晨4:00更新T-2日数据

xueqiu_sentiment_hourly
雪球小时情绪指数
2018.09.14
T日凌晨4:00更新T-2日数据

ecommerce_data
提供淘宝、天猫的电商销量数据
2014.01.01
T日凌晨4:00更新T-2日数据

在查询表数据时还可以指定所要查询的字段名，格式如下：query(库名.表名.字段名1，库名.表名.字段名2），多个字段用逗号分隔进行提取；query函数的更多用法详见：query简易教程
- filter(ssymmetry.ecommerce_data.date=='2019-04-14')：指定筛选条件，通过ssymmetry.ecommerce_data.date=='2019-04-14' 可以指定你想要查询的某天的电商数据；除此之外，还可以对表中其他字段指定筛选条件，如ssymmetry.ecommerce_data.sales>10000，表示销量超过10000的电商数据；多个筛选条件用英文逗号分隔。
- limit(n)：限制返回的数据条数，n指定返回条数。
- 返回结果：返回一个 dataframe，每一行对应数据表中的一条数据， 列索引是您所查询的字段名称

注意：

- 为了防止返回数据量过大, 我们每次最多返回5000行
- 不能进行连表查询，即同时查询多张表的数据

示例：

```python
# 查询2019年4月14日的电商数据
from jqdata import ssymmetry
df=ssymmetry.run_query(query(ssymmetry.ecommerce_data).filter(ssymmetry.ecommerce_data.date =='2019-04-14').limit(10))
print(df)

```

```python
         date market industry stock_code company        brand  sales  \
0  2019-04-14  非上市公司     家化日化       None    阿芙精油           阿芙    102   
1  2019-04-14  非上市公司     家化日化       None    阿芙精油           阿芙   5532   
2  2019-04-14     A股     电器行业  000016.sz    深康佳A  FRESTECH/新飞    225   
3  2019-04-14     A股     电器行业  000016.sz    深康佳A  FRESTECH/新飞     16   
4  2019-04-14     A股     电器行业  000016.sz    深康佳A     KONKA/康佳    300   
5  2019-04-14     A股     电器行业  000016.sz    深康佳A     KONKA/康佳    481   
6  2019-04-14     A股   服装家居鞋类  000026.sz    飞亚达A    Fiyta/飞亚达      4   
7  2019-04-14     A股   服装家居鞋类  000026.sz    飞亚达A    Fiyta/飞亚达     12   
8  2019-04-14     A股     电器行业  000063.sz    中兴通讯    nubia/努比亚    176   
9  2019-04-14     A股     电器行业  000063.sz    中兴通讯    nubia/努比亚     22   

        gmv  average_price  is_mall  
0    668256           6552        0  
1  85980593          15542        1  
2   2386014          10605        0  
3    568300          35519        1  
4  21835579          72785        0  
5  23682056          49235        1  
6    524180         131045        0  
7   1241799         103483        1  
8    892035           5068        0  
9   3277800         148991        1

```

### 数据字典
数据字典

#### 股吧天度情绪指数（guba_sentiment_daily）
股吧天度情绪指数（guba_sentiment_daily）

列名
类型
描述

date
date
日期

stock_code
str
股票代码

stock_name
str
股票名称

post_number
int
发帖数

read_number
int
阅读数

comment_number
int
评论数

sentiment
float
情绪指数

#### 股吧小时情绪指数（guba_sentiment_hourly）
股吧小时情绪指数（guba_sentiment_hourly）

列名
类型
描述

date
date
日期

time
date
时间

stock_code
str
股票代码

stock_name
str
股票名称

post_number
int
发帖数

read_number
int
阅读数

comment_number
int
评论数

sentiment
float
情绪指数

#### 雪球天度情绪指数（xueqiu_sentiment_daily）
雪球天度情绪指数（xueqiu_sentiment_daily）

列名
类型
描述

date
date
日期

stock_code
str
股票代码

stock_name
str
股票名称

post_count
int
发帖数

like_count
int
点赞数

reply_count
int
回复数

retweet_count
int
转发数

sentiment
float
情绪指数

#### 雪球小时情绪指数（xueqiu_sentiment_hourly）
雪球小时情绪指数（xueqiu_sentiment_hourly）

列名
类型
描述

date
date
日期

time
date
时间

stock_code
str
股票代码

stock_name
str
股票名称

post_count
int
发帖数

like_count
int
点赞数

reply_count
int
回复数

retweet_count
int
转发数

sentiment
float
情绪指数

#### 电商销量数据（ecommerce_data）
电商销量数据（ecommerce_data）

数据字典：

列名
类型
描述

date
date
日期

market
str
所属股票市场

industry
str
所属行业

stock_code
str
股票代码

company
str
公司名称

brand
str
品牌名称

sales
int
销量

gmv
int
销售额

average_price
int
均价

is_mall
int
平台标识（0-淘宝；1-天猫）