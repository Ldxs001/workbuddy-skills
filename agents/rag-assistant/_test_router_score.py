import sys
sys.path.insert(0, 'scripts')
from router import FallbackRouter

fb = FallbackRouter()
q1 = '习近平同志的核心思想有什么'
q2 = '习近平新时代中国特色社会主义思想核心要义 八个明确 十四个坚持 深入解读'
kw = '社会规划 文化宣教 中国共产党 国富论 文化倡导 习近平经济思想 计量分析 政治哲学 马克思 社会管理'

s1 = fb.score(q1, {'政经文哲': kw})
s2 = fb.score(q2, {'政经文哲': kw})
print(f'原问题 ({q1[:20]}...): {s1}')
print(f'改造后 ({q2[:20]}...): {s2}')
