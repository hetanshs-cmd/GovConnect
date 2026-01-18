from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# This acts as your "database" of dashboard modules
dashboard_configs = []

@app.route('/api/fields', methods=['POST'])
def add_dashboard_field():
    data = request.json
    
    # Improvised metadata fields
    new_field = {
        "id": len(dashboard_configs) + 1,
        "name": data.get('fieldName'),
        "category": data.get('fieldType'), # e.g., "Public Sector"
        "db_strategy": data.get('dbType'),
        "schema": data.get('inputs'), # The dynamic questions
        "created_at": "2026-01-18"
    }
    
    dashboard_configs.append(new_field)
    return jsonify({"message": "Field added successfully!", "data": new_field}), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)