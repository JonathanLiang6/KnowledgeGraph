import re
import jieba
import jieba.analyse

class EntityExtractor:
    """
    实体提取与分类核心逻辑类。
    完全解耦分词、分类和内容匹配，使用标题区间作为实体分类依据。
    """
    def __init__(self):
        # 停用词集合
        self.stop_words = set([
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '着', '或', 
            '一个', '没有', '我们', '你们', '他们', '她', '他', '它', '这', '那',
            '在', '有', '被', '对', '等', '能', '也', '会', '可', '到', '以', '为'
        ])
        
        # 关系匹配模式
        self.relation_patterns = {
            '包含': [r'包含|包括|涵盖|包含有|包括有|涵盖有'],
            '因果': [r'导致|引起|造成|使得|因为|由于|所以|因此'],
            '从属': [r'属于|隶属|归属于|是...的一部分|属于...的一部分'],
            '对立': [r'相反|对立|反对|冲突|矛盾|相反的|对立的'],
            '依赖': [r'依赖|依靠|依赖于|依靠于|需要|依赖关系'],
            '影响': [r'影响|作用|效果|影响到|作用于|效果是'],
            '属性': [r'是|具有|拥有|具备|特征是|特性是'],
            '关联': [r'关联|相关|有关|与...相关|与...有关'],
            '对比': [r'比较|对比|相比|与...相比|与...比较']
        }
        
        # 冷色调颜色体系，保证极高的区分度
        self.cold_color_palette = [
            '#2c3e50', '#2980b9', '#16a085', '#8e44ad', '#27ae60', 
            '#34495e', '#0097e6', '#487eb0', '#4cd137', '#192a56', 
            '#4b6584', '#3742fa', '#00a8ff', '#2f3640', '#5f27cd',
            '#10ac84', '#222f3e', '#576574', '#0abde3', '#341f97'
        ]
        self.entity_colors = {}
        self.color_index = 0

    def _get_color_for_type(self, entity_type):
        """为不同的实体类型分配不同的冷色调颜色"""
        if entity_type not in self.entity_colors:
            color = self.cold_color_palette[self.color_index % len(self.cold_color_palette)]
            self.entity_colors[entity_type] = color
            self.color_index += 1
        return self.entity_colors[entity_type]

    def extract(self, text):
        """
        基于标题边界区间匹配的实体提取。
        从当前标题起始位置到下一个标题的全部内容，均归为当前标题的实体类型。
        """
        lines = text.split('\n')
        blocks = []
        current_title = "通用概念"
        current_content = []
        
        # 1. 标题边界匹配规则
        for line in lines:
            title_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if title_match:
                if current_content:
                    blocks.append((current_title, '\n'.join(current_content)))
                
                raw_title = title_match.group(2).strip()
                # 过滤标题前的数字、特殊符号等无意义字符
                clean_title = re.sub(r'^[\d\.、一二三四五六七八九十]+', '', raw_title).strip()
                if not clean_title:
                    clean_title = raw_title
                
                # 限制标题长度作为类型名
                if len(clean_title) > 10:
                    clean_title = clean_title[:10]
                    
                current_title = clean_title
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            blocks.append((current_title, '\n'.join(current_content)))
            
        entities = []
        entity_id = 1
        entity_names = set()
        processed_sentences = []
        
        # 2. 过滤无意义分词、噪声词汇并按标题归类
        for title, content in blocks:
            sentences = re.split(r'[。！？.!?\n]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            block_words = []
            for sentence in sentences:
                words = jieba.cut(sentence)
                valid_words = [w for w in words if 
                               len(w.strip()) > 1 and 
                               w not in self.stop_words and 
                               not w.isdigit() and 
                               not re.match(r'^[^a-zA-Z\u4e00-\u9fa5]+$', w)]
                if valid_words:
                    processed_sentences.append((sentence, valid_words))
                    block_words.extend(valid_words)
                    
            if not block_words:
                continue
                
            # 提取区间内的高权重关键词
            keywords = jieba.analyse.extract_tags(' '.join(block_words), topK=20, withWeight=True)
            
            for keyword, weight in keywords:
                if keyword in entity_names:
                    continue
                
                # 分配实体颜色
                color = self._get_color_for_type(title)
                
                entities.append({
                    "id": str(entity_id),
                    "name": keyword,
                    "type": title,  # 严格按标题定义实体类型
                    "weight": weight,
                    "color": color
                })
                entity_names.add(keyword)
                entity_id += 1
                
        # 3. 关系抽取
        relationships = self._extract_relationships(entities, processed_sentences)
        return entities, relationships, self.entity_colors

    def _extract_relationships(self, entities, processed_sentences):
        """基于共现及模式匹配提取关系"""
        relationships = []
        relationship_id = 1
        entity_map = {entity["name"]: entity["id"] for entity in entities}
        
        for sentence, words in processed_sentences:
            sentence_entities = [word for word in words if word in entity_map]
            
            for i in range(len(sentence_entities)):
                for j in range(i + 1, len(sentence_entities)):
                    source = entity_map[sentence_entities[i]]
                    target = entity_map[sentence_entities[j]]
                    if source == target:
                        continue
                        
                    distance = abs(i - j)
                    weight = 1.0 / (distance + 1)
                    
                    relation_type = self._identify_relationship_type(sentence)
                    
                    exists = False
                    for rel in relationships:
                        if (rel["source"] == source and rel["target"] == target) or \
                           (rel["source"] == target and rel["target"] == source):
                            rel["value"] += weight
                            exists = True
                            break
                    
                    if not exists:
                        relationships.append({
                            "id": str(relationship_id),
                            "source": source,
                            "target": target,
                            "relation": relation_type,
                            "value": weight,
                            "sentence": sentence
                        })
                        relationship_id += 1
        return relationships

    def _identify_relationship_type(self, context):
        """基于上下文识别关系类型"""
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, context):
                    return relation_type
        return "关联"

    def optimize_graph(self, entities, relationships):
        """优化图谱结构，剔除冗余"""
        # 过滤低权重实体
        filtered_entities = [entity for entity in entities if entity["weight"] > 0.02]
        
        # 限制实体数量
        if len(filtered_entities) > 60:
            filtered_entities = sorted(filtered_entities, key=lambda x: x["weight"], reverse=True)[:60]
            
        entity_map = {entity["name"]: entity["id"] for entity in filtered_entities}
        
        filtered_relationships = []
        for rel in relationships:
            source_name = None
            target_name = None
            for entity in entities:
                if entity["id"] == rel["source"]:
                    source_name = entity["name"]
                if entity["id"] == rel["target"]:
                    target_name = entity["name"]
            
            if source_name in entity_map and target_name in entity_map:
                rel["source"] = entity_map[source_name]
                rel["target"] = entity_map[target_name]
                filtered_relationships.append(rel)
                
        # 限制关系数量
        if len(filtered_relationships) > 80:
            filtered_relationships = sorted(filtered_relationships, key=lambda x: x["value"], reverse=True)[:80]
            
        optimized_entities = []
        new_entity_map = {}
        for i, entity in enumerate(filtered_entities):
            new_id = str(i + 1)
            new_entity_map[entity["name"]] = new_id
            optimized_entities.append({
                "id": new_id,
                "name": entity["name"],
                "type": entity["type"],
                "weight": entity["weight"],
                "color": entity["color"]
            })
            
        optimized_relationships = []
        for i, rel in enumerate(filtered_relationships):
            source_name = None
            target_name = None
            for entity in filtered_entities:
                if entity["id"] == rel["source"]:
                    source_name = entity["name"]
                if entity["id"] == rel["target"]:
                    target_name = entity["name"]
            
            if source_name and target_name:
                optimized_relationships.append({
                    "id": str(i + 1),
                    "source": new_entity_map[source_name],
                    "target": new_entity_map[target_name],
                    "relation": rel["relation"],
                    "value": rel["value"],
                    "sentence": rel["sentence"]
                })
                
        return optimized_entities, optimized_relationships
