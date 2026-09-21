SCHEMA = {
    "patients": {
        "description": "Patient demographic data",
        "columns": {
            "patient_id": {"type": "INTEGER", "description": "Primary key for patient"},
            "first_name": {"type": "VARCHAR", "description": "Patient first name"},
            "last_name": {"type": "VARCHAR", "description": "Patient last name"},
            "gender": {"type": "VARCHAR", "description": "Gender of patient"},
            "date_of_birth": {"type": "DATE", "description": "Date of birth"},
            "zip_code": {"type": "VARCHAR", "description": "Postal code"},
            "city": {"type": "VARCHAR", "description": "City"},
            "state": {"type": "VARCHAR", "description": "State"},
            "created_at": {"type": "TIMESTAMP", "description": "Record creation time"}
        }
    },
    "conditions": {
        "description": "Patient medical conditions and diagnoses",
        "columns": {
            "condition_id": {"type": "INTEGER", "description": "Primary key for condition"},
            "patient_id": {"type": "INTEGER", "description": "Foreign key to patients"},
            "encounter_id": {"type": "INTEGER", "description": "Foreign key to encounters"},
            "onset_date": {"type": "DATE", "description": "Onset date of condition"},
            "condition_desc": {"type": "VARCHAR", "description": "Description of condition"},
            "condition_code": {"type": "VARCHAR", "description": "Medical code for condition"},
            "resolved_date": {"type": "DATE", "description": "Resolution date"},
            "created_at": {"type": "TIMESTAMP", "description": "Record creation time"}
        }
    },
    "encounters": {
        "description": "Hospital visits and clinical encounters",
        "columns": {
            "encounter_id": {"type": "INTEGER", "description": "Primary key for encounter"},
            "patient_id": {"type": "INTEGER", "description": "Foreign key to patients"},
            "encounter_date": {"type": "DATE", "description": "Date of encounter"},
            "encounter_type": {"type": "VARCHAR", "description": "Type of encounter"},
            "provider": {"type": "VARCHAR", "description": "Healthcare provider"},
            "reason_code": {"type": "VARCHAR", "description": "Reason code"},
            "reason_desc": {"type": "VARCHAR", "description": "Reason description"},
            "created_at": {"type": "TIMESTAMP", "description": "Record creation time"}
        }
    },
    "medications": {
        "description": "Medications prescribed to patients",
        "columns": {
            "medication_id": {"type": "INTEGER", "description": "Primary key for medication"},
            "patient_id": {"type": "INTEGER", "description": "Foreign key to patients"},
            "encounter_id": {"type": "INTEGER", "description": "Foreign key to encounters"},
            "drug_code": {"type": "VARCHAR", "description": "Drug code"},
            "drug_name": {"type": "VARCHAR", "description": "Name of prescribed drug"},
            "start_date": {"type": "DATE", "description": "Prescription start date"},
            "end_date": {"type": "DATE", "description": "Prescription end date"},
            "created_at": {"type": "TIMESTAMP", "description": "Record creation time"}
        }
    },
    "observations": {
        "description": "Patient lab tests and vital observations",
        "columns": {
            "observation_id": {"type": "INTEGER", "description": "Primary key for observation"},
            "patient_id": {"type": "INTEGER", "description": "Foreign key to patients"},
            "encounter_id": {"type": "INTEGER", "description": "Foreign key to encounters"},
            "obs_code": {"type": "VARCHAR", "description": "Observation code"},
            "obs_desc": {"type": "VARCHAR", "description": "Observation description"},
            "obs_value": {"type": "VARCHAR", "description": "Observation value"},
            "obs_unit": {"type": "VARCHAR", "description": "Unit of measurement"},
            "obs_date": {"type": "DATE", "description": "Date of observation"},
            "created_at": {"type": "TIMESTAMP", "description": "Record creation time"}
        }
    }
}