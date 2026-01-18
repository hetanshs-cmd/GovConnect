import React, { useState } from 'react';

interface MakesectionsProps {
	isDark: boolean;
}

const Makesections: React.FC<MakesectionsProps> = ({ isDark }) => {
	const [isOpen, setIsOpen] = useState(false);
	const [formData, setFormData] = useState({
		fieldName: '',
		fieldType: 'Healthcare',
		dbType: 'Save to Database',
		inputs: [{ label: '', type: 'text' }]
	});

	// Handle dynamic sub-field addition
	const addSubField = () => {
		setFormData({
			...formData,
			inputs: [...formData.inputs, { label: '', type: 'text' }]
		});
	};

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		const response = await fetch('/api/fields', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify(formData)
		});
		if (response.ok) {
			const result = await response.json();

			// Create section for navigation
			const sectionId = Date.now().toString();
			const sectionPath = `/${formData.fieldName.toLowerCase().replace(/\s+/g, '-')}`;

			const existingSections = JSON.parse(localStorage.getItem('dynamic_full_sections') || '[]');
			const fullSectionData = {
				id: sectionId,
				title: formData.fieldName,
				path: sectionPath,
				icon: 'Database',
				table_name: result.data.table_name,
				fields: formData.inputs.map(input => ({
					name: input.label,
					type: input.type === 'number' ? 'int' : input.type === 'boolean' ? 'bool' : 'string',
					required: false,
					show_ui: true
				})),
				description: `${formData.fieldType} - ${formData.dbType}`
			};
			localStorage.setItem('dynamic_full_sections', JSON.stringify([...existingSections, fullSectionData]));

			alert("New Dashboard Field Integrated!");
			setIsOpen(false);
			// Trigger layout reload
			window.dispatchEvent(new CustomEvent('sectionsUpdated'));
		} else {
			alert("Failed to add field");
		}
	};

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex justify-between items-center">
				<div>
					<h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>
						Dashboard Field Manager
					</h2>
					<p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
						Create dynamic dashboard fields with custom data inputs
					</p>
				</div>
				<button
					onClick={() => setIsOpen(true)}
					className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${isDark
						? 'bg-blue-600 hover:bg-blue-700 text-white'
						: 'bg-blue-500 hover:bg-blue-600 text-white'
						}`}
				>
					+ Add New Field
				</button>
			</div>

			{isOpen && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
					<div className={`w-full max-w-2xl p-6 rounded-lg ${isDark ? 'bg-gray-800 text-white' : 'bg-white text-black'} max-h-[90vh] overflow-y-auto`}>
						<h2 className="text-xl font-bold mb-4">Configure New Field</h2>
						<form onSubmit={handleSubmit}>
							<div className="space-y-4">
								<div>
									<label className="block text-sm font-medium mb-1">Field Name:</label>
									<input
										type="text"
										placeholder="e.g. Agriculture"
										value={formData.fieldName}
										onChange={e => setFormData({ ...formData, fieldName: e.target.value })}
										required
										className={`w-full px-3 py-2 border rounded-lg ${isDark
											? 'bg-gray-700 border-gray-600 text-white'
											: 'bg-white border-gray-300 text-black'
											}`}
									/>
								</div>

								<div>
									<label className="block text-sm font-medium mb-1">Field Type:</label>
									<select
										value={formData.fieldType}
										onChange={e => setFormData({ ...formData, fieldType: e.target.value })}
										className={`w-full px-3 py-2 border rounded-lg ${isDark
											? 'bg-gray-700 border-gray-600 text-white'
											: 'bg-white border-gray-300 text-black'
											}`}
									>
										<option value="Healthcare">Healthcare</option>
										<option value="Agriculture">Agriculture</option>
										<option value="Finance">Finance</option>
									</select>
								</div>

								<div>
									<label className="block text-sm font-medium mb-1">Database Strategy:</label>
									<select
										value={formData.dbType}
										onChange={e => setFormData({ ...formData, dbType: e.target.value })}
										className={`w-full px-3 py-2 border rounded-lg ${isDark
											? 'bg-gray-700 border-gray-600 text-white'
											: 'bg-white border-gray-300 text-black'
											}`}
									>
										<option value="Save to DB">Save to Database</option>
										<option value="Visualize Only">Make a Dashboard Only</option>
									</select>
								</div>

								<hr className={`my-4 ${isDark ? 'border-gray-600' : 'border-gray-300'}`} />
								<h4 className="text-lg font-semibold">Define Data Inputs</h4>
								{formData.inputs.map((input, index) => (
									<div key={index} className="flex items-center space-x-2">
										<input
											placeholder="Input Label (e.g. Age)"
											value={input.label}
											onChange={e => {
												const newInputs = [...formData.inputs];
												newInputs[index].label = e.target.value;
												setFormData({ ...formData, inputs: newInputs });
											}}
											className={`flex-1 px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										/>
										<select
											value={input.type}
											onChange={e => {
												const newInputs = [...formData.inputs];
												newInputs[index].type = e.target.value;
												setFormData({ ...formData, inputs: newInputs });
											}}
											className={`px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										>
											<option value="text">Text</option>
											<option value="number">Number</option>
											<option value="boolean">Yes/No</option>
										</select>
									</div>
								))}

								<button
									type="button"
									onClick={addSubField}
									className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
								>
									+ Add Sub-Field
								</button>
							</div>

							<div className="flex justify-end space-x-3 mt-6">
								<button
									type="button"
									onClick={() => setIsOpen(false)}
									className={`px-4 py-2 border rounded-lg ${isDark
										? 'border-gray-600 text-gray-300 hover:bg-gray-700'
										: 'border-gray-300 text-gray-700 hover:bg-gray-50'
										}`}
								>
									Cancel
								</button>
								<button
									type="submit"
									className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
								>
									Save Configuration
								</button>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	);
};

export default Makesections;