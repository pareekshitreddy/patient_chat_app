from neo4j import GraphDatabase

class Neo4jDriver:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def save_entities(self, patient_name, entities):
        with self.driver.session() as session:
            session.write_transaction(self._save_entities_tx, patient_name, entities)

    @staticmethod
    def _save_entities_tx(tx, patient_name, entities):
        tx.run("""
            MERGE (p:Patient {name: $patient_name})
            WITH p
            UNWIND $entities AS entity
            MERGE (e:Entity {type: entity.type, value: entity.value})
            MERGE (p)-[:MENTIONED]->(e)
        """, patient_name=patient_name, entities=[{'type': k, 'value': v} for k, v in entities.items()])
