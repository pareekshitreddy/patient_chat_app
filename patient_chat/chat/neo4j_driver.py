class Neo4jDriver:
    def __init__(self, uri, user, password):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def save_entities(self, patient_name, entities):
        with self.driver.session() as session:
            for key, value in entities.items():
                if value:
                    session.run(
                        """
                        MERGE (p:Patient {{name: $patient_name}})
                        MERGE (e:Entity {{name: $value}})
                        MERGE (p)-[:HAS_{}]->(e)
                        """.format(key.upper()),
                        patient_name=patient_name,
                        value=value
                    )


    def get_patient_knowledge(self, patient_name):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Patient {name: $patient_name})-[r]->(e)
                RETURN type(r) as relationship, e.name as entity
                """,
                patient_name=patient_name
            )
            knowledge = {}
            for record in result:
                relationship = record["relationship"].replace('HAS_', '').lower()
                entity = record["entity"]
                knowledge[relationship] = entity
            return knowledge
