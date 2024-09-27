class Neo4jDriver:
    def __init__(self, uri, user, password):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def save_patient_data(self, patient):
        with self.driver.session() as session:
            # Prepare properties dictionary, excluding None values
            patient_properties = {
                'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
                'phone_number': patient.phone_number,
                'email': patient.email,
                'medical_condition': patient.medical_condition,
                'medication_regimen': patient.medication_regimen,
                'last_appointment': str(patient.last_appointment) if patient.last_appointment else None,
                'next_appointment': str(patient.next_appointment) if patient.next_appointment else None,
                'doctor_name': patient.doctor_name,
                'lab_tests': patient.lab_tests,
                'vital_signs': patient.vital_signs,
                'weight': patient.weight
            }
            # Remove keys with None values to prevent overwriting
            patient_properties = {k: v for k, v in patient_properties.items() if v is not None}
            # Build SET clause dynamically
            set_clause = ', '.join([f'p.{k} = ${k}' for k in patient_properties.keys()])

            query = f"""
                MERGE (p:Patient {{name: $patient_name}})
                SET {set_clause}
            """
            params = {'patient_name': f"{patient.first_name} {patient.last_name}"}
            params.update(patient_properties)

            session.run(query, **params)

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
            # Get patient properties
            result_props = session.run(
                """
                MATCH (p:Patient {name: $patient_name})
                RETURN properties(p) as patient_props
                """,
                patient_name=patient_name
            )
            patient_props = {}
            record_props = result_props.single()
            if record_props:
                patient_props = record_props["patient_props"]

            # Get related entities
            result_entities = session.run(
                """
                MATCH (p:Patient {name: $patient_name})-[r]->(e)
                RETURN type(r) as relationship, e.name as entity
                """,
                patient_name=patient_name
            )
            entities = {}
            for record in result_entities:
                relationship = record["relationship"].replace('HAS_', '').lower()
                entity = record["entity"]
                # Handle multiple entities per relationship type
                if relationship in entities:
                    if isinstance(entities[relationship], list):
                        entities[relationship].append(entity)
                    else:
                        entities[relationship] = [entities[relationship], entity]
                else:
                    entities[relationship] = entity

            # Combine properties and entities
            knowledge = {**patient_props, **entities}
            return knowledge
