"""
文本相似度算法模块
使用 TF-IDF + 余弦相似度计算两段中文文本的相似程度
用于作业查重、内容比对等场景
"""

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_text_similarity(text1, text2):
    """
    计算两段文本的 TF-IDF 余弦相似度
    返回 0.0 到 100.0 之间的查重率
    
    Args:
        text1: 第一段文本（如学生作业）
        text2: 第二段文本（如参考答案或其他学生作业）
    
    Returns:
        float: 相似度百分比 (0.0 - 100.0)
    """
    if not text1 or not text2:
        return 0.0
    
    # 去除空白字符
    text1 = str(text1 or "").strip()
    text2 = str(text2 or "").strip()
    
    if not text1 or not text2:
        return 0.0
        
    try:
        # 1. 使用 jieba 进行中文分词，并用空格拼接
        words1 = " ".join(jieba.cut(text1))
        words2 = " ".join(jieba.cut(text2))
        
        # 2. 构建 TF-IDF 向量提取器
        vectorizer = TfidfVectorizer()
        
        # 3. 将分词后的文本转化为 TF-IDF 矩阵
        tfidf_matrix = vectorizer.fit_transform([words1, words2])
        
        # 4. 计算余弦相似度 (Cosine Similarity)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # 返回百分比，保留两位小数
        return round(float(similarity) * 100, 2)
    except Exception as e:
        print(f"查重算法计算失败: {e}")
        return 0.0


def calculate_multi_text_similarity(reference_text, candidate_texts):
    """
    计算一段参考文本与多段候选文本的相似度
    
    Args:
        reference_text: 参考文本
        candidate_texts: 候选文本列表
    
    Returns:
        list: 包含每个候选文本的相似度结果
              [{'text_index': 0, 'similarity': 85.23}, ...]
    """
    if not reference_text or not candidate_texts:
        return []
    
    results = []
    for idx, candidate in enumerate(candidate_texts):
        similarity = calculate_text_similarity(reference_text, candidate)
        results.append({
            'text_index': idx,
            'similarity': similarity
        })
    
    # 按相似度降序排序
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results
