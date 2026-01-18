import React, { useState, useEffect } from 'react';
import { Plus, Database, Table, Eye, EyeOff, Save, RefreshCw } from 'lucide-react';

interface DynamicDatabaseProps {
	isDark: boolean;
	user: any;
}

interface TableMetadata {
	table_name: string;
	fields: Array<{
		field_name: string;
		data_type: string;
		show_ui: boolean;
	}>;
}

interface TableData {
	table_name: string;
	data: any[];
	ui_only: boolean;
}

const DynamicDatabase: React.FC<DynamicDatabaseProps> = ({ isDark, user }) => {
	const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create');
	const [tables, setTables] = useState<string[]>([]);
	const [selectedTable, setSelectedTable] = useState<string>('');
	const [tableMetadata, setTableMetadata] = useState<TableMetadata | null>(null);
	const [tableData, setTableData] = useState<TableData | null>(null);
	const [loading, setLoading] = useState(false);
	const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

	// Form state for creating tables
	const [tableName, setTableName] = useState('');
	const [fields, setFields] = useState<Array<{ name: string; type: string; showUI: boolean }>>([
		{ name: '', type: 'string', showUI: true }
	]);

	// Form state for inserting data
	const [insertData, setInsertData] = useState<Record<string, any>>({});

	const API_BASE_URL = '/api';

	// Get auth token - not needed since we use cookies
	// const getAuthToken = () => {
	//   return localStorage.getItem('auth_token');
	// };
	const fetchTables = async () => {
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables`, {
				credentials: 'include'
			});

			if (response.ok) {
				const data = await response.json();
				setTables(data.tables);
			} else {
				setMessage({ type: 'error', text: 'Failed to fetch tables' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error fetching tables' });
		}
		setLoading(false);
	};

	// Fetch table metadata
	const fetchTableMetadata = async (tableName: string) => {
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables/${tableName}/metadata`, {
				credentials: 'include'
			});

			if (response.ok) {
				const data = await response.json();
				setTableMetadata(data);
			} else {
				setMessage({ type: 'error', text: 'Failed to fetch table metadata' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error fetching table metadata' });
		}
		setLoading(false);
	};

	// Fetch table data
	const fetchTableData = async (tableName: string, uiOnly = true) => {
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables/${tableName}/data?ui_only=${uiOnly}`, {
				credentials: 'include'
			});

			if (response.ok) {
				const data = await response.json();
				setTableData(data);
			} else {
				setMessage({ type: 'error', text: 'Failed to fetch table data' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error fetching table data' });
		}
		setLoading(false);
	};

	// Setup dynamic database
	const setupDatabase = async () => {
		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/setup`, {
				method: 'POST',
				credentials: 'include'
			});

			if (response.ok) {
				setMessage({ type: 'success', text: 'Dynamic database initialized successfully' });
				fetchTables();
			} else {
				const error = await response.json();
				setMessage({ type: 'error', text: error.error || 'Failed to setup database' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error setting up database' });
		}
		setLoading(false);
	};

	// Create new table
	const createTable = async () => {
		if (!tableName.trim()) {
			setMessage({ type: 'error', text: 'Table name is required' });
			return;
		}

		const validFields = fields.filter(f => f.name.trim());
		if (validFields.length === 0) {
			setMessage({ type: 'error', text: 'At least one field is required' });
			return;
		}

		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify({
					table_name: tableName,
					fields: validFields.map(f => f.name),
					data_types: validFields.map(f => f.type),
					show_ui: validFields.map(f => f.showUI)
				})
			});

			if (response.ok) {
				setMessage({ type: 'success', text: `Table "${tableName}" created successfully` });
				setTableName('');
				setFields([{ name: '', type: 'string', showUI: true }]);
				fetchTables();
			} else {
				const error = await response.json();
				setMessage({ type: 'error', text: error.error || 'Failed to create table' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error creating table' });
		}
		setLoading(false);
	};

	// Insert data into table
	const insertDataIntoTable = async () => {
		if (!selectedTable) {
			setMessage({ type: 'error', text: 'Please select a table' });
			return;
		}

		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables/${selectedTable}/data`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify(insertData)
			});

			if (response.ok) {
				setMessage({ type: 'success', text: 'Data inserted successfully' });
				setInsertData({});
				fetchTableData(selectedTable);
			} else {
				const error = await response.json();
				setMessage({ type: 'error', text: error.error || 'Failed to insert data' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error inserting data' });
		}
		setLoading(false);
	};

	// Add new field to form
	const addField = () => {
		setFields([...fields, { name: '', type: 'string', showUI: true }]);
	};

	// Update field
	const updateField = (index: number, key: string, value: any) => {
		const newFields = [...fields];
		newFields[index] = { ...newFields[index], [key]: value };
		setFields(newFields);
	};

	// Remove field
	const removeField = (index: number) => {
		if (fields.length > 1) {
			setFields(fields.filter((_, i) => i !== index));
		}
	};

	// Delete table
	const deleteTable = async (tableName: string) => {
		if (!confirm(`Are you sure you want to delete the table "${tableName}"? This action cannot be undone and will delete all data in the table.`)) {
			return;
		}

		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables/${tableName}`, {
				method: 'DELETE',
				credentials: 'include'
			});

			if (response.ok) {
				setTables(tables.filter(t => t !== tableName));
				if (selectedTable === tableName) {
					setSelectedTable('');
					setTableMetadata(null);
					setTableData(null);
				}
				setMessage({ type: 'success', text: `Table "${tableName}" deleted successfully` });
			} else {
				const error = await response.json();
				setMessage({ type: 'error', text: error.error || 'Failed to delete table' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error deleting table' });
		}
		setLoading(false);
	};

	// Delete field
	const deleteField = async (tableName: string, fieldName: string) => {
		if (!confirm(`Are you sure you want to delete the field "${fieldName}"? This action cannot be undone and will delete all data in this field.`)) {
			return;
		}

		setLoading(true);
		try {
			const response = await fetch(`${API_BASE_URL}/admin/dynamic/tables/${tableName}/fields/${fieldName}`, {
				method: 'DELETE',
				credentials: 'include'
			});

			if (response.ok) {
				// Refresh table metadata
				fetchTableMetadata(tableName);
				fetchTableData(tableName);
				setMessage({ type: 'success', text: `Field "${fieldName}" deleted successfully` });
			} else {
				const error = await response.json();
				setMessage({ type: 'error', text: error.error || 'Failed to delete field' });
			}
		} catch (error) {
			setMessage({ type: 'error', text: 'Error deleting field' });
		}
		setLoading(false);
	};

	useEffect(() => {
		fetchTables();
	}, []);

	// Clear message after 5 seconds
	useEffect(() => {
		if (message) {
			const timer = setTimeout(() => setMessage(null), 5000);
			return () => clearTimeout(timer);
		}
	}, [message]);

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>
						Dynamic Database Management
					</h2>
					<p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
						Create and manage custom data tables
					</p>
				</div>
				<button
					onClick={setupDatabase}
					disabled={loading}
					className={`px-4 py-2 rounded-lg font-medium transition-colors ${isDark
						? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-blue-800'
						: 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-blue-400'
						}`}
				>
					{loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Initialize DB'}
				</button>
			</div>

			{/* Message */}
			{message && (
				<div className={`p-4 rounded-lg ${message.type === 'success'
					? 'bg-green-100 text-green-800 border border-green-200'
					: 'bg-red-100 text-red-800 border border-red-200'
					}`}>
					{message.text}
				</div>
			)}

			{/* Tab Navigation */}
			<div className="flex border-b border-gray-200 dark:border-gray-700">
				<button
					onClick={() => setActiveTab('create')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'create'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					Create Table
				</button>
				<button
					onClick={() => setActiveTab('manage')}
					className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === 'manage'
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: `border-transparent ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`
						}`}
				>
					Manage Data
				</button>
			</div>

			{/* Create Table Tab */}
			{activeTab === 'create' && (
				<div className="space-y-6">
					<div className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
						<h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-black'}`}>
							Create New Table
						</h3>

						{/* Table Name */}
						<div className="mb-4">
							<label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
								Table Name
							</label>
							<input
								type="text"
								value={tableName}
								onChange={(e) => setTableName(e.target.value)}
								placeholder="Enter table name"
								className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
									? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
									: 'bg-white border-gray-300 text-black placeholder-gray-500'
									}`}
							/>
						</div>

						{/* Fields */}
						<div className="space-y-4">
							<div className="flex items-center justify-between">
								<label className={`block text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
									Fields
								</label>
								<button
									onClick={addField}
									className={`px-3 py-1 rounded text-sm font-medium transition-colors ${isDark
										? 'bg-green-600 hover:bg-green-700 text-white'
										: 'bg-green-500 hover:bg-green-600 text-white'
										}`}
								>
									<Plus className="w-4 h-4 inline mr-1" />
									Add Field
								</button>
							</div>

							{fields.map((field, index) => (
								<div key={index} className="flex items-center space-x-4 p-4 border rounded-lg">
									<div className="flex-1">
										<input
											type="text"
											value={field.name}
											onChange={(e) => updateField(index, 'name', e.target.value)}
											placeholder="Field name"
											className={`w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
												? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
												: 'bg-white border-gray-300 text-black placeholder-gray-500'
												}`}
										/>
									</div>
									<div className="w-32">
										<select
											value={field.type}
											onChange={(e) => updateField(index, 'type', e.target.value)}
											className={`w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										>
											<option value="string">String</option>
											<option value="text">Text</option>
											<option value="int">Integer</option>
											<option value="float">Float</option>
											<option value="bool">Boolean</option>
											<option value="date">Date</option>
										</select>
									</div>
									<div className="flex items-center">
										<input
											type="checkbox"
											checked={field.showUI}
											onChange={(e) => updateField(index, 'showUI', e.target.checked)}
											className="mr-2"
										/>
										<label className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
											Show in UI
										</label>
									</div>
									{fields.length > 1 && (
										<button
											onClick={() => removeField(index)}
											className={`px-2 py-1 rounded text-sm font-medium transition-colors ${isDark
												? 'bg-red-600 hover:bg-red-700 text-white'
												: 'bg-red-500 hover:bg-red-600 text-white'
												}`}
										>
											Remove
										</button>
									)}
								</div>
							))}
						</div>

						<button
							onClick={createTable}
							disabled={loading}
							className={`w-full mt-6 px-4 py-2 rounded-lg font-medium transition-colors ${isDark
								? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-blue-800'
								: 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-blue-400'
								}`}
						>
							{loading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
							Create Table
						</button>
					</div>
				</div>
			)}

			{/* Manage Data Tab */}
			{activeTab === 'manage' && (
				<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
					{/* Tables List */}
					<div className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
						<h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-black'}`}>
							Tables
						</h3>
						<div className="space-y-2">
							{tables.map((table) => (
								<div key={table} className="flex items-center justify-between">
									<button
										onClick={() => handleTableSelect(table)}
										className={`flex-1 text-left px-3 py-2 rounded transition-colors ${selectedTable === table
											? isDark ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-800'
											: isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'
											}`}
									>
										<Table className="w-4 h-4 inline mr-2" />
										{table}
									</button>
									<button
										onClick={() => deleteTable(table)}
										disabled={loading}
										className="ml-2 p-2 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
										title="Delete Table"
									>
										<Trash2 className="w-4 h-4" />
									</button>
								</div>
							))}
							{tables.length === 0 && (
								<p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
									No tables found. Create one first.
								</p>
							)}
						</div>
					</div>

					{/* Table Metadata */}
					<div className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
						<h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-black'}`}>
							Table Structure
						</h3>
						{tableMetadata ? (
							<div className="space-y-3">
								<h4 className={`font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
									{tableMetadata.table_name}
								</h4>
								<div className="space-y-2">
									{tableMetadata.fields.map((field) => (
										<div key={field.field_name} className="flex items-center justify-between text-sm">
											<span className={isDark ? 'text-gray-300' : 'text-gray-700'}>
												{field.field_name}
											</span>
											<div className="flex items-center space-x-2">
												<span className={`px-2 py-1 rounded text-xs ${field.data_type === 'string' ? 'bg-blue-100 text-blue-800' :
													field.data_type === 'int' ? 'bg-green-100 text-green-800' :
														field.data_type === 'text' ? 'bg-purple-100 text-purple-800' :
															field.data_type === 'date' ? 'bg-orange-100 text-orange-800' :
																'bg-gray-100 text-gray-800'
													}`}>
													{field.data_type}
												</span>
												{field.show_ui ? (
													<Eye className="w-4 h-4 text-green-500" />
												) : (
													<EyeOff className="w-4 h-4 text-gray-400" />
												)}
												<button
													onClick={() => deleteField(tableMetadata.table_name, field.field_name)}
													disabled={loading}
													className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
													title="Delete Field"
												>
													<Trash2 className="w-3 h-3" />
												</button>
											</div>
										</div>
									))}
								</div>
							</div>
						) : (
							<p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
								Select a table to view its structure
							</p>
						)}
					</div>

					{/* Data Management */}
					<div className={`p-6 rounded-lg ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
						<h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-black'}`}>
							Data Management
						</h3>
						{selectedTable && tableMetadata ? (
							<div className="space-y-4">
								{/* Insert Data Form */}
								<div>
									<h4 className={`font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
										Insert New Record
									</h4>
									<div className="space-y-2">
										{tableMetadata.fields.map((field) => (
											<div key={field.field_name}>
												<label className={`block text-sm mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
													{field.field_name}
												</label>
												<input
													type={field.data_type === 'int' ? 'number' :
														field.data_type === 'float' ? 'number' :
															field.data_type === 'date' ? 'date' :
																field.data_type === 'bool' ? 'checkbox' : 'text'}
													value={insertData[field.field_name] || ''}
													onChange={(e) => {
														const value = field.data_type === 'bool' ? e.target.checked :
															field.data_type === 'int' ? parseInt(e.target.value) || 0 :
																field.data_type === 'float' ? parseFloat(e.target.value) || 0 :
																	e.target.value;
														setInsertData({ ...insertData, [field.field_name]: value });
													}}
													className={`w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark
														? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
														: 'bg-white border-gray-300 text-black placeholder-gray-500'
														}`}
												/>
											</div>
										))}
									</div>
									<button
										onClick={insertDataIntoTable}
										disabled={loading}
										className={`w-full mt-3 px-4 py-2 rounded-lg font-medium transition-colors ${isDark
											? 'bg-green-600 hover:bg-green-700 text-white disabled:bg-green-800'
											: 'bg-green-500 hover:bg-green-600 text-white disabled:bg-green-400'
											}`}
									>
										{loading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
										Insert Data
									</button>
								</div>

								{/* View Data */}
								<div>
									<div className="flex items-center justify-between mb-2">
										<h4 className={`font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
											Records ({tableData?.data.length || 0})
										</h4>
										<button
											onClick={() => fetchTableData(selectedTable)}
											disabled={loading}
											className={`px-3 py-1 rounded text-sm transition-colors ${isDark
												? 'bg-gray-600 hover:bg-gray-700 text-white'
												: 'bg-gray-500 hover:bg-gray-600 text-white'
												}`}
										>
											<RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
										</button>
									</div>
									<div className={`max-h-64 overflow-y-auto border rounded ${isDark ? 'border-gray-600' : 'border-gray-300'
										}`}>
										{tableData?.data.length ? (
											<table className="w-full text-sm">
												<thead className={isDark ? 'bg-gray-700' : 'bg-gray-50'}>
													<tr>
														{Object.keys(tableData.data[0]).map((key) => (
															<th key={key} className={`px-3 py-2 text-left font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'
																}`}>
																{key}
															</th>
														))}
													</tr>
												</thead>
												<tbody>
													{tableData.data.map((row, index) => (
														<tr key={index} className={isDark ? 'border-t border-gray-600' : 'border-t border-gray-200'}>
															{Object.values(row).map((value: any, i) => (
																<td key={i} className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-700'
																	}`}>
																	{String(value)}
																</td>
															))}
														</tr>
													))}
												</tbody>
											</table>
										) : (
											<p className={`text-sm p-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
												No data found
											</p>
										)}
									</div>
								</div>
							</div>
						) : (
							<p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
								Select a table to manage data
							</p>
						)}
					</div>
				</div>
			)}
		</div>
	);
};

export default DynamicDatabase;