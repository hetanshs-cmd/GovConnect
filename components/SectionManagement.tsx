import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Settings, Save, X, Eye, EyeOff } from 'lucide-react';

interface Section {
	id: string;
	title: string;
	displayName: string;
	description: string;
	icon: string;
	enabled: boolean;
	order: number;
	createdAt: string;
	updatedAt: string;
	table_name: string;
	fields: Array<{
		name: string;
		type: string;
		required: boolean;
		show_ui: boolean;
	}>;
}

interface SectionManagementProps {
	isDark: boolean;
	user: any;
}

const SectionManagement: React.FC<SectionManagementProps> = ({ isDark, user }) => {
	const [sections, setSections] = useState<Section[]>([]);
	const [loading, setLoading] = useState(true);
	const [showAddForm, setShowAddForm] = useState(false);
	const [editingSection, setEditingSection] = useState<Section | null>(null);
	const [formData, setFormData] = useState({
		title: '',
		displayName: '',
		description: '',
		icon: 'Database',
		enabled: true,
		order: 0,
		fields: [{ name: '', type: 'string', required: false, show_ui: true }]
	});

	const API_BASE_URL = import.meta.env.VITE_API_URL || '';

	useEffect(() => {
		fetchSections();
	}, []);

	const fetchSections = async () => {
		try {
			// Load sections from localStorage (dynamic_full_sections)
			const savedSections = localStorage.getItem('dynamic_full_sections');
			if (savedSections) {
				const parsedSections = JSON.parse(savedSections);
				setSections(parsedSections.map((s: any) => ({
					id: s.id,
					title: s.title,
					displayName: s.title,
					description: s.description || '',
					icon: s.icon || 'Database',
					enabled: true,
					order: 0,
					createdAt: new Date().toISOString(),
					updatedAt: new Date().toISOString(),
					table_name: s.table_name,
					fields: s.fields || []
				})));
			}
		} catch (error) {
			console.error('Failed to fetch sections:', error);
		} finally {
			setLoading(false);
		}
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		try {
			// Create dynamic table first
			const tableName = `section_${Date.now()}`;
			const validFields = formData.fields.filter(f => f.name.trim());

			if (validFields.length === 0) {
				alert('At least one field is required');
				return;
			}

			const response = await fetch(`${API_BASE_URL}/api/admin/dynamic/tables`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({
					table_name: tableName,
					fields: validFields.map(f => f.name),
					data_types: validFields.map(f => f.type),
					show_ui: validFields.map(f => f.show_ui)
				})
			});

			if (response.ok) {
				// Create section data
				const sectionData = {
					id: Date.now().toString(),
					title: formData.title,
					displayName: formData.displayName,
					description: formData.description,
					icon: formData.icon,
					enabled: formData.enabled,
					order: formData.order,
					createdAt: new Date().toISOString(),
					updatedAt: new Date().toISOString(),
					table_name: tableName,
					fields: validFields
				};

				// Add to localStorage
				const existingSections = JSON.parse(localStorage.getItem('dynamic_full_sections') || '[]');
				const fullSectionData = {
					id: sectionData.id,
					title: sectionData.title,
					path: `/${sectionData.title.toLowerCase().replace(/\s+/g, '-')}`,
					icon: sectionData.icon,
					table_name: tableName,
					fields: validFields,
					description: sectionData.description
				};
				localStorage.setItem('dynamic_full_sections', JSON.stringify([...existingSections, fullSectionData]));

				// Update state
				setSections(prev => [...prev, sectionData]);
				resetForm();

				// Trigger layout reload by dispatching custom event
				window.dispatchEvent(new CustomEvent('sectionsUpdated'));
			} else {
				const error = await response.json();
				alert(`Failed to create section: ${error.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Failed to save section:', error);
			alert('Failed to create section');
		}
	};

	const handleDelete = async (sectionId: string) => {
		if (!confirm('Are you sure you want to delete this section? This will remove the section page and all its data.')) {
			return;
		}

		try {
			// Remove from localStorage
			const existingSections = JSON.parse(localStorage.getItem('dynamic_full_sections') || '[]');
			const updatedSections = existingSections.filter((s: any) => s.id !== sectionId);
			localStorage.setItem('dynamic_full_sections', JSON.stringify(updatedSections));

			// Update state
			setSections(prev => prev.filter(s => s.id !== sectionId));

			// Trigger layout reload
			window.dispatchEvent(new CustomEvent('sectionsUpdated'));
		} catch (error) {
			console.error('Failed to delete section:', error);
		}
	};

	const toggleSection = async (sectionId: string, enabled: boolean) => {
		try {
			// Update in localStorage
			const existingSections = JSON.parse(localStorage.getItem('dynamic_full_sections') || '[]');
			const updatedSections = existingSections.map((s: any) =>
				s.id === sectionId ? { ...s, enabled } : s
			);
			localStorage.setItem('dynamic_full_sections', JSON.stringify(updatedSections));

			// Update state
			setSections(prev => prev.map(s => s.id === sectionId ? { ...s, enabled } : s));

			// Trigger layout reload
			window.dispatchEvent(new CustomEvent('sectionsUpdated'));
		} catch (error) {
			console.error('Failed to toggle section:', error);
		}
	};

	const resetForm = () => {
		setFormData({
			title: '',
			displayName: '',
			description: '',
			icon: 'Database',
			enabled: true,
			order: 0,
			fields: [{ name: '', type: 'string', required: false, show_ui: true }]
		});
		setShowAddForm(false);
		setEditingSection(null);
	};

	const addField = () => {
		setFormData(prev => ({
			...prev,
			fields: [...prev.fields, { name: '', type: 'string', required: false, show_ui: true }]
		}));
	};

	const updateField = (index: number, key: string, value: any) => {
		const newFields = [...formData.fields];
		newFields[index] = { ...newFields[index], [key]: value };
		setFormData(prev => ({ ...prev, fields: newFields }));
	};

	const removeField = (index: number) => {
		if (formData.fields.length > 1) {
			setFormData(prev => ({
				...prev,
				fields: prev.fields.filter((_, i) => i !== index)
			}));
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-8">
				<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex justify-between items-center">
				<div>
					<h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>
						Section Management
					</h2>
					<p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
						Create and manage dynamic service sections that users can fill out
					</p>
				</div>
				<button
					onClick={() => setShowAddForm(true)}
					className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${isDark
						? 'bg-blue-600 hover:bg-blue-700 text-white'
						: 'bg-blue-500 hover:bg-blue-600 text-white'
						}`}
				>
					<Plus className="w-4 h-4 mr-2" />
					Create Section
				</button>
			</div>

			{/* Sections List */}
			<div className={`rounded-lg border ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
				{sections.length === 0 ? (
					<div className="p-8 text-center">
						<p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
							No sections created yet. Click "Create Section" to get started.
						</p>
					</div>
				) : (
					<div className="divide-y divide-gray-200 dark:divide-gray-700">
						{sections.map((section) => (
							<div key={section.id} className="p-4 flex items-center justify-between">
								<div className="flex-1">
									<h3 className={`font-semibold ${isDark ? 'text-white' : 'text-black'}`}>
										{section.title}
									</h3>
									<p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
										{section.description || 'No description'}
									</p>
									<p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
										Table: {section.table_name} • {section.fields.length} fields
									</p>
								</div>
								<div className="flex items-center space-x-2">
									<button
										onClick={() => toggleSection(section.id, !section.enabled)}
										className={`p-2 rounded ${section.enabled
											? 'text-green-500 hover:bg-green-100 dark:hover:bg-green-900'
											: 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
											}`}
										title={section.enabled ? 'Disable section' : 'Enable section'}
									>
										{section.enabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
									</button>
									<button
										onClick={() => handleDelete(section.id)}
										className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900 rounded"
										title="Delete section"
									>
										<Trash2 className="w-4 h-4" />
									</button>
								</div>
							</div>
						))}
					</div>
				)}
			</div>

			{/* Add/Edit Form Modal */}
			{showAddForm && (
				<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
					<div className={`w-full max-w-2xl p-6 rounded-lg ${isDark ? 'bg-gray-800 text-white' : 'bg-white text-black'} max-h-[90vh] overflow-y-auto`}>
						<h2 className="text-xl font-bold mb-4">
							Create New Section
						</h2>

						<form onSubmit={handleSubmit}>
							<div className="space-y-4">
								{/* Basic Info */}
								<div className="grid grid-cols-2 gap-4">
									<div>
										<label className="block text-sm font-medium mb-1">Title *</label>
										<input
											type="text"
											value={formData.title}
											onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
											className={`w-full px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
											required
										/>
									</div>
									<div>
										<label className="block text-sm font-medium mb-1">Display Name</label>
										<input
											type="text"
											value={formData.displayName}
											onChange={(e) => setFormData(prev => ({ ...prev, displayName: e.target.value }))}
											className={`w-full px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										/>
									</div>
								</div>

								<div>
									<label className="block text-sm font-medium mb-1">Description</label>
									<textarea
										value={formData.description}
										onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
										rows={3}
										className={`w-full px-3 py-2 border rounded-lg ${isDark
											? 'bg-gray-700 border-gray-600 text-white'
											: 'bg-white border-gray-300 text-black'
											}`}
									/>
								</div>

								<div className="grid grid-cols-2 gap-4">
									<div>
										<label className="block text-sm font-medium mb-1">Icon</label>
										<select
											value={formData.icon}
											onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
											className={`w-full px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										>
											<option value="Database">Database</option>
											<option value="FileText">File Text</option>
											<option value="Building2">Building</option>
											<option value="Users">Users</option>
											<option value="Globe">Globe</option>
											<option value="Truck">Truck</option>
											<option value="Home">Home</option>
											<option value="Briefcase">Briefcase</option>
											<option value="HeartPulse">Heart Pulse</option>
											<option value="Sprout">Sprout</option>
										</select>
									</div>
									<div>
										<label className="block text-sm font-medium mb-1">Order</label>
										<input
											type="number"
											value={formData.order}
											onChange={(e) => setFormData(prev => ({ ...prev, order: parseInt(e.target.value) || 0 }))}
											className={`w-full px-3 py-2 border rounded-lg ${isDark
												? 'bg-gray-700 border-gray-600 text-white'
												: 'bg-white border-gray-300 text-black'
												}`}
										/>
									</div>
								</div>

								{/* Fields */}
								<div>
									<div className="flex justify-between items-center mb-2">
										<label className="block text-sm font-medium">Fields</label>
										<button
											type="button"
											onClick={addField}
											className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"
										>
											Add Field
										</button>
									</div>
									<div className="space-y-2">
										{formData.fields.map((field, index) => (
											<div key={index} className="flex items-center space-x-2 p-2 border rounded">
												<input
													type="text"
													placeholder="Field name"
													value={field.name}
													onChange={(e) => updateField(index, 'name', e.target.value)}
													className={`flex-1 px-2 py-1 border rounded ${isDark
														? 'bg-gray-700 border-gray-600 text-white'
														: 'bg-white border-gray-300 text-black'
														}`}
												/>
												<select
													value={field.type}
													onChange={(e) => updateField(index, 'type', e.target.value)}
													className={`px-2 py-1 border rounded ${isDark
														? 'bg-gray-700 border-gray-600 text-white'
														: 'bg-white border-gray-300 text-black'
														}`}
												>
													<option value="string">Text</option>
													<option value="text">Long Text</option>
													<option value="int">Number</option>
													<option value="float">Decimal</option>
													<option value="bool">Yes/No</option>
													<option value="date">Date</option>
												</select>
												<label className="flex items-center">
													<input
														type="checkbox"
														checked={field.required}
														onChange={(e) => updateField(index, 'required', e.target.checked)}
														className="mr-1"
													/>
													Required
												</label>
												<label className="flex items-center">
													<input
														type="checkbox"
														checked={field.show_ui}
														onChange={(e) => updateField(index, 'show_ui', e.target.checked)}
														className="mr-1"
													/>
													Show
												</label>
												{formData.fields.length > 1 && (
													<button
														type="button"
														onClick={() => removeField(index)}
														className="p-1 text-red-500 hover:bg-red-100 rounded"
													>
														<X className="w-4 h-4" />
													</button>
												)}
											</div>
										))}
									</div>
								</div>
							</div>

							<div className="flex justify-end space-x-3 mt-6">
								<button
									type="button"
									onClick={resetForm}
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
									Create Section
								</button>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	);
};

export default SectionManagement;