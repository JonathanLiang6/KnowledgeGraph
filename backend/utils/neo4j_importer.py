"""
知识图谱数据导入模块
将GraphRAG生成的Parquet格式数据导入Neo4j图数据库
支持实体、关系、社区、文档等多种节点类型的导入
"""

import time
import logging
from typing import Optional
import pandas as pd
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jImporter:
    """
    Neo4j图数据库导入器类
    负责将GraphRAG生成的知识图谱数据导入Neo4j数据库
    """
    
    def __init__(self):
        """初始化Neo4j连接"""
        self.driver = None
        self.database = config.neo4j.database
        self.batch_size = config.neo4j.batch_size
        self._connect()
        
    def _connect(self) -> None:
        """建立与Neo4j数据库的连接"""
        try:
            self.driver = GraphDatabase.driver(
                config.neo4j.uri,
                auth=(config.neo4j.username, config.neo4j.password)
            )
            # 验证连接
            self.driver.verify_connectivity()
            logger.info(f"成功连接到Neo4j数据库: {config.neo4j.uri}")
        except ServiceUnavailable as e:
            logger.error(f"无法连接到Neo4j数据库: {e}")
            raise
        except AuthError as e:
            logger.error(f"Neo4j认证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接Neo4j时发生未知错误: {e}")
            raise
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭")
    
    def create_constraints(self) -> None:
        """
        创建数据库约束和索引
        确保节点ID的唯一性，提高查询效率
        """
        # 定义需要创建的约束语句
        constraints = [
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:__Document__) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:__Chunk__) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:__Entity__) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:__Entity__) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT community_id IF NOT EXISTS FOR (c:__Community__) REQUIRE c.community IS UNIQUE",
            "CREATE CONSTRAINT covariate_title IF NOT EXISTS FOR (c:__Covariate__) REQUIRE c.title IS UNIQUE",
        ]
        
        logger.info("开始创建数据库约束...")
        for statement in constraints:
            try:
                self._execute_query(statement)
                logger.debug(f"执行约束: {statement[:50]}...")
            except Exception as e:
                logger.warning(f"创建约束失败: {e}")
        logger.info("数据库约束创建完成")
    
    def _execute_query(self, query: str, parameters: Optional[dict] = None) -> None:
        """
        执行单个Cypher查询
        
        参数:
            query: Cypher查询语句
            parameters: 查询参数
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters)
            result.consume()
    
    def batch_import(
        self, 
        statement: str, 
        df: pd.DataFrame, 
        label: str = "数据"
    ) -> int:
        """
        批量导入数据到Neo4j
        
        参数:
            statement: Cypher导入语句（使用$value引用行数据）
            df: 要导入的Pandas数据框
            label: 数据标签，用于日志显示
            
        返回:
            导入的总行数
        """
        total = len(df)
        if total == 0:
            logger.warning(f"{label}数据为空，跳过导入")
            return 0
            
        start_time = time.time()
        logger.info(f"开始导入{label}，共{total}条记录...")
        
        # 使用UNWIND批量导入
        full_statement = "UNWIND $rows AS value " + statement
        
        # 分批处理
        for start in range(0, total, self.batch_size):
            end = min(start + self.batch_size, total)
            batch = df.iloc[start:end]
            
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(
                        full_statement,
                        rows=batch.to_dict('records')
                    )
                    summary = result.consume()
                    logger.debug(f"批次 {start//self.batch_size + 1}: 导入{len(batch)}条记录")
            except Exception as e:
                logger.error(f"导入批次失败 (行{start}-{end}): {e}")
                raise
        
        elapsed = time.time() - start_time
        logger.info(f"{label}导入完成: {total}行，耗时{elapsed:.2f}秒")
        return total
    
    def import_documents(self) -> int:
        """
        导入文档节点
        从create_final_documents.parquet读取文档数据
        """
        file_path = config.get_artifact_path("create_final_documents.parquet")
        
        try:
            df = pd.read_parquet(file_path, columns=["id", "title", "raw_content"])
        except FileNotFoundError:
            logger.warning(f"文档文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取文档文件失败: {e}")
            return 0
        
        # Cypher语句：合并文档节点并设置属性
        statement = """
        MERGE (d:__Document__ {id: value.id})
        SET d += value {.title, .raw_content, .id}
        """
        
        return self.batch_import(statement, df, "文档")
    
    def import_chunks(self) -> int:
        """
        导入文本块节点及与文档的关系
        从create_final_text_units.parquet读取文本块数据
        """
        file_path = config.get_artifact_path("create_final_text_units.parquet")
        
        try:
            df = pd.read_parquet(
                file_path,
                columns=["id", "text", "n_tokens", "document_ids", 
                        "entity_ids", "relationship_ids", "covariate_ids"]
            )
        except FileNotFoundError:
            logger.warning(f"文本块文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取文本块文件失败: {e}")
            return 0
        
        # Cypher语句：创建文本块节点并建立与文档的PART_OF关系
        statement = """
        MERGE (c:__Chunk__ {id: value.id})
        SET c += value {.text, .n_tokens, .id}
        WITH c, value
        UNWIND value.document_ids AS document_id
        MATCH (d:__Document__ {id: document_id})
        MERGE (c)-[:PART_OF]->(d)
        """
        
        return self.batch_import(statement, df, "文本块")
    
    def import_entities(self) -> int:
        """
        导入实体节点及与文本块的关系
        从create_final_entities.parquet读取实体数据
        支持向量属性设置和动态标签添加
        """
        file_path = config.get_artifact_path("create_final_entities.parquet")
        
        try:
            df = pd.read_parquet(
                file_path,
                columns=["name", "type", "description", "human_readable_id",
                        "id", "description_embedding", "text_unit_ids"]
            )
        except FileNotFoundError:
            logger.warning(f"实体文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取实体文件失败: {e}")
            return 0
        
        # Cypher语句：创建实体节点，设置向量属性，添加类型标签，建立与文本块的关系
        statement = """
        MERGE (e:__Entity__ {id: value.id})
        SET e += value {.name, .type, .description, .human_readable_id, .id, .text_unit_ids}
        WITH e, value
        CALL db.create.setNodeVectorProperty(e, "description_embedding", value.description_embedding)
        CALL apoc.create.addLabels(e, 
            CASE 
                WHEN coalesce(value.type, "") = "" THEN []
                ELSE [apoc.text.upperCamelCase(replace(value.type, '"', ''))]
            END
        ) YIELD node
        WITH e, value
        UNWIND value.text_unit_ids AS text_unit_id
        MATCH (c:__Chunk__ {id: text_unit_id})
        MERGE (c)-[:HAS_ENTITY]->(e)
        """
        
        return self.batch_import(statement, df, "实体")
    
    def import_relationships(self) -> int:
        """
        导入实体之间的关系
        从create_final_relationships.parquet读取关系数据
        """
        file_path = config.get_artifact_path("create_final_relationships.parquet")
        
        try:
            df = pd.read_parquet(
                file_path,
                columns=["source", "target", "id", "rank", "weight",
                        "human_readable_id", "description", "text_unit_ids"]
            )
        except FileNotFoundError:
            logger.warning(f"关系文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取关系文件失败: {e}")
            return 0
        
        # Cypher语句：在源实体和目标实体之间创建RELATED关系
        statement = """
        MATCH (source:__Entity__ {name: replace(value.source, '"', '')})
        MATCH (target:__Entity__ {name: replace(value.target, '"', '')})
        MERGE (source)-[rel:RELATED {id: value.id}]->(target)
        SET rel += value {.rank, .weight, .human_readable_id, .description, .text_unit_ids}
        """
        
        return self.batch_import(statement, df, "关系")
    
    def import_community_reports(self) -> int:
        """
        导入社区报告节点
        从create_final_community_reports.parquet读取社区报告数据
        """
        file_path = config.get_artifact_path("create_final_community_reports.parquet")
        
        try:
            df = pd.read_parquet(
                file_path,
                columns=["id", "community", "findings", "title", "summary",
                        "level", "rank", "rank_explanation", "full_content"]
            )
        except FileNotFoundError:
            logger.warning(f"社区报告文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取社区报告文件失败: {e}")
            return 0
        
        # Cypher语句：创建社区节点并关联发现
        statement = """
        MERGE (c:__Community__ {id: value.id})
        SET c += value {.community, .level, .title, .rank, .rank_explanation, .full_content, .summary}
        WITH c, value
        UNWIND range(0, size(value.findings) - 1) AS finding_idx
        WITH c, value, finding_idx, value.findings[finding_idx] AS finding
        MERGE (c)-[:HAS_FINDING]->(f:Finding {id: finding_idx})
        SET f += finding
        """
        
        return self.batch_import(statement, df, "社区报告")
    
    def import_communities(self) -> int:
        """
        导入社区与文本块、实体的关联关系
        从create_final_communities.parquet读取社区数据
        """
        file_path = config.get_artifact_path("create_final_communities.parquet")
        
        try:
            df = pd.read_parquet(
                file_path,
                columns=["id", "level", "title", "text_unit_ids", "relationship_ids"]
            )
        except FileNotFoundError:
            logger.warning(f"社区文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取社区文件失败: {e}")
            return 0
        
        # Cypher语句：建立社区与文本块、实体的关系
        statement = """
        MERGE (c:__Community__ {community: value.id})
        SET c += value {.level}
        WITH *
        UNWIND value.text_unit_ids AS text_unit_id
        MATCH (t:__Chunk__ {id: text_unit_id})
        MERGE (c)-[:HAS_CHUNK]->(t)
        WITH *
        UNWIND value.relationship_ids AS rel_id
        MATCH (start:__Entity__)-[:RELATED {id: rel_id}]->(end:__Entity__)
        MERGE (start)-[:IN_COMMUNITY]->(c)
        MERGE (end)-[:IN_COMMUNITY]->(c)
        """
        
        return self.batch_import(statement, df, "社区关联")
    
    def import_covariates(self) -> int:
        """
        导入协变量节点及与文本块的关系
        从create_final_covariates.parquet读取协变量数据
        """
        file_path = config.get_artifact_path("create_final_covariates.parquet")
        
        try:
            df = pd.read_parquet(file_path)
        except FileNotFoundError:
            logger.warning(f"协变量文件不存在: {file_path}")
            return 0
        except Exception as e:
            logger.error(f"读取协变量文件失败: {e}")
            return 0
        
        # Cypher语句：创建协变量节点并建立与文本块的关系
        statement = """
        MERGE (c:__Covariate__ {id: value.id})
        SET c += apoc.map.clean(value, ["text_unit_id", "document_ids", "n_tokens"], [NULL, ""])
        WITH c, value
        MATCH (ch:__Chunk__ {id: value.text_unit_id})
        MERGE (ch)-[:HAS_COVARIATE]->(c)
        """
        
        return self.batch_import(statement, df, "协变量")
    
    def import_all(self) -> dict:
        """
        执行完整的知识图谱数据导入流程
        
        返回:
            包含各类节点导入数量的字典
        """
        logger.info("=" * 50)
        logger.info("开始知识图谱数据导入")
        logger.info("=" * 50)
        
        start_time = time.time()
        results = {}
        
        # 第1步：创建约束
        self.create_constraints()
        
        # 第2步：导入文档
        results["documents"] = self.import_documents()
        
        # 第3步：导入文本块
        results["chunks"] = self.import_chunks()
        
        # 第4步：导入实体
        results["entities"] = self.import_entities()
        
        # 第5步：导入关系
        results["relationships"] = self.import_relationships()
        
        # 第6步：导入社区报告
        results["community_reports"] = self.import_community_reports()
        
        # 第7步：导入社区关联
        results["communities"] = self.import_communities()
        
        # 第8步：导入协变量
        results["covariates"] = self.import_covariates()
        
        elapsed = time.time() - start_time
        total = sum(results.values())
        
        logger.info("=" * 50)
        logger.info("知识图谱数据导入完成")
        logger.info(f"总耗时: {elapsed:.2f}秒")
        logger.info(f"总记录数: {total}")
        logger.info("导入统计:")
        for key, value in results.items():
            logger.info(f"  - {key}: {value}")
        logger.info("=" * 50)
        
        return results


def main():
    """主函数：执行知识图谱数据导入"""
    importer = None
    try:
        # 创建导入器实例
        importer = Neo4jImporter()
        
        # 执行完整导入
        results = importer.import_all()
        
        # 输出结果摘要
        print("\n" + "=" * 50)
        print("导入完成摘要:")
        print("=" * 50)
        for key, value in results.items():
            print(f"  {key}: {value}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"导入过程发生错误: {e}")
        raise
    finally:
        if importer:
            importer.close()


if __name__ == "__main__":
    main()
