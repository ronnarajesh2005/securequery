# track_b/schemas/mock_schema.py

SCHEMA = {
    "patients": {
        "description": "Basic demographic information about patients.",
        "columns": {
            "id": {
                "type": "integer",
                "description": "Unique patient identifier",
                "pii": False
            },
            "birth_date": {
                "type": "date",
                "description": "Patient date of birth",
                "pii": False
            },
            "gender": {
                "type": "string",
                "description": "Patient gender",
                "pii": False
            },
            "race": {
                "type": "string",
                "description": "Patient race",
                "pii": False
            },
            "ethnicity": {
                "type": "string",
                "description": "Patient ethnicity",
                "pii": False
            },
            "hospital_id": {
                "type": "string",
                "description": "Hospital identifier",
                "pii": False
            }
        }
    },

    "conditions": {
        "description": "Medical conditions diagnosed for patients.",
        "columns": {
            "id": {
                "type": "integer",
                "description": "Condition record identifier",
                "pii": False
            },
            "patient_id": {
                "type": "integer",
                "description": "Reference to patients.id",
                "pii": False
            },
            "description": {
                "type": "string",
                "description": "Name of the medical condition",
                "pii": False
            },
            "start_date": {
                "type": "date",
                "description": "Condition start date",
                "pii": False
            },
            "hospital_id": {
                "type": "string",
                "description": "Hospital where the condition was recorded",
                "pii": False
            }
        }
    },

    "medications": {
        "description": "Medication records for patients.",
        "columns": {
            "id": {
                "type": "integer",
                "description": "Medication record identifier",
                "pii": False
            },
            "patient_id": {
                "type": "integer",
                "description": "Reference to patients.id",
                "pii": False
            },
            "description": {
                "type": "string",
                "description": "Medication name",
                "pii": False
            },
            "start_date": {
                "type": "date",
                "description": "Medication start date",
                "pii": False
            },
            "hospital_id": {
                "type": "string",
                "description": "Hospital where medication was recorded",
                "pii": False
            }
        }
    },

    "encounters": {
        "description": "Patient healthcare encounters.",
        "columns": {
            "id": {
                "type": "integer",
                "description": "Encounter identifier",
                "pii": False
            },
            "patient_id": {
                "type": "integer",
                "description": "Reference to patients.id",
                "pii": False
            },
            "encounter_type": {
                "type": "string",
                "description": "Type of healthcare encounter",
                "pii": False
            },
            "start_date": {
                "type": "date",
                "description": "Encounter start date",
                "pii": False
            },
            "end_date": {
                "type": "date",
                "description": "Encounter end date",
                "pii": False
            },
            "hospital_id": {
                "type": "string",
                "description": "Hospital where encounter occurred",
                "pii": False
            }
        }
    },

    "observations": {
        "description": "Clinical measurements and observations.",
        "columns": {
            "id": {
                "type": "integer",
                "description": "Observation identifier",
                "pii": False
            },
            "patient_id": {
                "type": "integer",
                "description": "Reference to patients.id",
                "pii": False
            },
            "code": {
                "type": "string",
                "description": "Observation code",
                "pii": False
            },
            "description": {
                "type": "string",
                "description": "Observation description",
                "pii": False
            },
            "value": {
                "type": "float",
                "description": "Observation numeric value",
                "pii": False
            },
            "unit": {
                "type": "string",
                "description": "Observation unit",
                "pii": False
            },
            "observation_date": {
                "type": "date",
                "description": "Date of observation",
                "pii": False
            },
            "hospital_id": {
                "type": "string",
                "description": "Hospital where observation was recorded",
                "pii": False
            }
        }
    }
}