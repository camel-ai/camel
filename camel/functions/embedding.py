documents = [
    '藜（读音lí）麦（Chenopodium\xa0quinoa\xa0Willd.）是藜科藜属植物。穗部可呈红、紫、黄，植株形状类似灰灰菜，成熟后穗部类似高粱穗。植株大小受环境及遗传因素影响较大，从0.3-3米不等，茎部质地较硬，可分枝可不分。单叶互生，叶片呈鸭掌状，叶缘分为全缘型与锯齿缘型。藜麦花两性，花序呈伞状、穗状、圆锥状，藜麦种子较小，呈小圆药片状，直径1.5-2毫米，千粒重1.4-3克。\xa0[1]\xa0\n原产于南美洲安第斯山脉的哥伦比亚、厄瓜多尔、秘鲁等中高海拔山区。具有一定的耐旱、耐寒、耐盐性，生长范围约为海平面到海拔4500米左右的高原上，最适的高度为海拔3000-4000米的高原或山地地区。\xa0[1]\xa0\n藜麦富含的维生素、多酚、类黄酮类、皂苷和植物甾醇类物质具有多种健康功效。藜麦具有高蛋白，其所含脂肪中不饱和脂肪酸占83%，还是一种低果糖低葡萄糖的食物，能在糖脂代谢过程中发挥有益功效。\xa0[1]\xa0\xa0[5]\xa0\n国内藜麦产品的销售以电商为主,缺乏实体店销售,藜麦市场有待进一步完善。藜麦国际市场需求强劲,发展前景十分广阔。通过加快品种培育和生产加工设备研发,丰富产品种类,藜麦必将在“调结构,转方式,保增收”的农业政策落实中发挥重要作用。\xa0[5]\xa0\n2022年5月，“超级谷物”藜麦在宁洱县试种成功。',
    '藜麦是印第安人的传统主食，几乎和水稻同时被驯服有着6000多年的种植和食用历史。藜麦具有相当全面营养成分，并且藜麦的口感口味都容易被人接受。在藜麦这种营养丰富的粮食滋养下南美洲的印第安人创造了伟大的印加文明，印加人将藜麦尊为粮食之母。美国人早在80年代就将藜麦引入NASA，作为宇航员的日常口粮，FAO认定藜麦是唯一一种单作物即可满足人类所需的全部营养的粮食，并进行藜麦的推广和宣传。2013年是联合国钦定的国际藜麦年。以此呼吁人们注意粮食安全和营养均衡。',
    '藜麦穗部可呈红、紫、黄，植株形状类似灰灰菜，成熟后穗部类似高粱穗。植株大小受环境及遗传因素影响较大，从0.3-3米不等，茎部质地较硬，可分枝可不分。单叶互生，叶片呈鸭掌状，叶缘分为全缘型与锯齿缘型。根系庞大但分布较浅，根上的须根多，吸水能力强。藜麦花两性，花序呈伞状、穗状、圆锥状，藜麦种子较小，呈小圆药片状，直径1.5-2毫米，千粒重1.4-3克。',
    '原产于南美洲安第斯山脉的哥伦比亚、厄瓜多尔、秘鲁等中高海拔山区。具有一定的耐旱、耐寒、耐盐性，生长范围约为海平面到海拔4500米左右的高原上，最适的高度为海拔3000-4000米的高原或山地地区。\n\n播前准备',
    '繁殖\n地块选择：应选择地势较高、阳光充足、通风条件好及肥力较好的地块种植。藜麦不宜重茬，忌连作，应合理轮作倒茬。前茬以大豆、薯类最好，其次是玉米、高粱等。\xa0[4]\xa0\n施肥整地：早春土壤刚解冻，趁气温尚低、土壤水分蒸发慢的时候，施足底肥，达到土肥融合，壮伐蓄水。播种前每降1次雨及时耙耱1次，做到上虚下实，干旱时只耙不耕，并进行压实处理。一般每亩（667平方米/亩，下同）施腐熟农家肥1000-2000千克、硫酸钾型复合肥20-30千克。如果土壤比较贫瘠，可适当增加复合肥的施用量。\xa0[4]',
]

import openai
import pandas as pd
import os
from ast import literal_eval

# Chroma's client library for Python
import chromadb

# I've set this to our new embeddings model, this can be changed to the embedding model of your choice
EMBEDDING_MODEL = "text-embedding-ada-002"

chroma_client = chromadb.EphemeralClient()
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# embeddings_url = 'https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip'

# # The file is ~700 MB so this will take some time
# wget.download(embeddings_url)

# import zipfile
# with zipfile.ZipFile("vector_database_wikipedia_articles_embedded.zip","r") as zip_ref:
#     zip_ref.extractall("../data")

article_df = pd.read_csv('vector_database.csv')[:1000]

article_df.to_csv('vector_database1.csv')
