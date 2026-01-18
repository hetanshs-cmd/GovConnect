import React, { useState, useEffect } from 'react';

interface PageManagementProps {
	isDark: boolean;
	user: any;
}

interface Page {
	id: number;
	title: string;
	description: string;
	route: string;
	icon: string;
	isActive: boolean;
	isBuiltin: boolean;
	isMainTab: boolean;
	createdBy: number;
	createdAt: string;
	updatedAt: string;
}

const PageManagement: React.FC<PageManagementProps> = ({ isDark, user }) => {
	const [pages, setPages] = useState<Page[]>([]);
	const [loading, setLoading] = useState(true);
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [editingPage, setEditingPage] = useState<Page | null>(null);

	useEffect(() => {
		loadPages();
	}, []);

	const loadPages = async () => {
		try {
			setLoading(true);
			const response = await fetch('/api/admin/pages', {
				credentials: 'include',
			});

			if (response.ok) {
				const data = await response.json();
				setPages(data);
			}
		} catch (error) {
			console.error('Failed to load pages:', error);
		} finally {
			setLoading(false);
		}
	};

	const handleCreatePage = async (pageData: Omit<Page, 'id' | 'createdBy' | 'createdAt' | 'updatedAt'>) => {
		try {
			const response = await fetch('/api/admin/pages', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				credentials: 'include',
				body: JSON.stringify(pageData),
			});

			if (response.ok) {
				const newPage = await response.json();
				setPages(prev => [...prev, newPage]);
				setShowCreateModal(false);
			}
		} catch (error) {
			console.error('Failed to create page:', error);
		}
	};

	const handleUpdatePage = async (pageId: number, pageData: Partial<Page>) => {
		try {
			const response = await fetch(`/api/admin/pages/${pageId}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
				},
				credentials: 'include',
				body: JSON.stringify(pageData),
			});

			if (response.ok) {
				const updatedPage = await response.json();
				setPages(prev => prev.map(page => page.id === pageId ? updatedPage : page));
				setEditingPage(null);
			}
		} catch (error) {
			console.error('Failed to update page:', error);
		}
	};

	const handleDeletePage = async (pageId: number) => {
		if (!confirm('Are you sure you want to delete this page?')) return;

		try {
			const response = await fetch(`/api/admin/pages/${pageId}`, {
				method: 'DELETE',
				credentials: 'include',
			});

			if (response.ok) {
				setPages(prev => prev.filter(page => page.id !== pageId));
			}
		} catch (error) {
			console.error('Failed to delete page:', error);
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
				<h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-black'}`}>
					Page Management
				</h2>
				<button
					onClick={() => setShowCreateModal(true)}
					className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
				>
					Create New Page
				</button>
			</div>

			{/* Pages List */}
			<div className={`rounded-lg border ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
				{pages.length === 0 ? (
					<div className="p-8 text-center">
						<p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
							No pages created yet. Click "Create New Page" to get started.
						</p>
					</div>
				) : (
					<div className="divide-y divide-gray-200 dark:divide-gray-700">
						{pages.map((page) => (
							<div key={page.id} className="p-4 flex items-center justify-between">
								<div className="flex-1">
									<h3 className={`font-semibold ${isDark ? 'text-white' : 'text-black'}`}>
										{page.title}
									</h3>
									<p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
										{page.description || 'No description'}
									</p>
									<p className={`text-xs mt-1 font-mono ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
										Route: {page.route}
									</p>
								</div>
								<div className="flex items-center space-x-2">
									<span className={`px-2 py-1 text-xs rounded ${page.isActive
										? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
										: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
										}`}>
										{page.isActive ? 'Active' : 'Inactive'}
									</span>
									<button
										onClick={() => setEditingPage(page)}
										className={`px-3 py-1 text-sm rounded ${isDark ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
											}`}
									>
										Edit
									</button>
									{!page.isBuiltin && (
										<button
											onClick={() => handleDeletePage(page.id)}
											className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
										>
											Delete
										</button>
									)}
								</div>
							</div>
						))}
					</div>
				)}
			</div>

			{/* Create Page Modal */}
			{showCreateModal && (
				<PageModal
					isDark={isDark}
					onSave={handleCreatePage}
					onClose={() => setShowCreateModal(false)}
				/>
			)}

			{/* Edit Page Modal */}
			{editingPage && (
				<PageModal
					isDark={isDark}
					page={editingPage}
					onSave={(data) => handleUpdatePage(editingPage.id, data)}
					onClose={() => setEditingPage(null)}
				/>
			)}
		</div>
	);
};

// Page Modal Component
interface PageModalProps {
	isDark: boolean;
	page?: Page;
	onSave: (data: Omit<Page, 'id' | 'createdBy' | 'createdAt' | 'updatedAt'>) => void;
	onClose: () => void;
}

const PageModal: React.FC<PageModalProps> = ({ isDark, page, onSave, onClose }) => {
	const [formData, setFormData] = useState({
		title: page?.title || '',
		description: page?.description || '',
		route: page?.route || '',
		icon: page?.icon || 'FileText',
		isActive: page?.isActive ?? true,
		isMainTab: page?.isMainTab ?? false,
		isBuiltin: page?.isBuiltin ?? false,
	});

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		onSave(formData);
	};

	const handleChange = (field: string, value: string | boolean) => {
		setFormData(prev => ({
			...prev,
			[field]: value
		}));
	};

	return (
		<div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div className={`w-full max-w-md p-6 rounded-lg ${isDark ? 'bg-gray-800 text-white' : 'bg-white text-black'}`}>
				<h2 className="text-xl font-bold mb-4">
					{page ? 'Edit Page' : 'Create New Page'}
				</h2>

				<form onSubmit={handleSubmit}>
					<div className="space-y-4">
						<div>
							<label className="block text-sm font-medium mb-1">Title *</label>
							<input
								type="text"
								value={formData.title}
								onChange={(e) => handleChange('title', e.target.value)}
								className={`w-full px-3 py-2 border rounded-lg ${isDark
									? 'bg-gray-700 border-gray-600 text-white'
									: 'bg-white border-gray-300 text-black'
									}`}
								required
							/>
						</div>

						<div>
							<label className="block text-sm font-medium mb-1">Description</label>
							<textarea
								value={formData.description}
								onChange={(e) => handleChange('description', e.target.value)}
								rows={3}
								className={`w-full px-3 py-2 border rounded-lg ${isDark
									? 'bg-gray-700 border-gray-600 text-white'
									: 'bg-white border-gray-300 text-black'
									}`}
							/>
						</div>

						<div>
							<label className="block text-sm font-medium mb-1">Route *</label>
							<input
								type="text"
								value={formData.route}
								onChange={(e) => handleChange('route', e.target.value)}
								placeholder="/my-page"
								className={`w-full px-3 py-2 border rounded-lg ${isDark
									? 'bg-gray-700 border-gray-600 text-white'
									: 'bg-white border-gray-300 text-black'
									}`}
								required
							/>
							<p className="text-xs mt-1 text-gray-500">
								Must start with '/' (e.g., /my-custom-page)
							</p>
						</div>

						<div>
							<label className="block text-sm font-medium mb-1">Icon</label>
							<select
								value={formData.icon}
								onChange={(e) => handleChange('icon', e.target.value)}
								className={`w-full px-3 py-2 border rounded-lg ${isDark
									? 'bg-gray-700 border-gray-600 text-white'
									: 'bg-white border-gray-300 text-black'
									}`}
							>
								<option value="FileText">File Text</option>
								<option value="Building2">Building</option>
								<option value="Users">Users</option>
								<option value="Database">Database</option>
								<option value="Globe">Globe</option>
								<option value="Truck">Truck</option>
								<option value="Home">Home</option>
								<option value="Briefcase">Briefcase</option>
							</select>
						</div>

						<div className="flex items-center">
							<input
								type="checkbox"
								id="isActive"
								checked={formData.isActive}
								onChange={(e) => handleChange('isActive', e.target.checked)}
								className="mr-2"
							/>
							<label htmlFor="isActive" className="text-sm font-medium">
								Active
							</label>
						</div>

						<div className="flex items-center">
							<input
								type="checkbox"
								id="isMainTab"
								checked={formData.isMainTab}
								onChange={(e) => handleChange('isMainTab', e.target.checked)}
								className="mr-2"
							/>
							<label htmlFor="isMainTab" className="text-sm font-medium">
								Main Navigation Tab
							</label>
							<p className="text-xs ml-2 text-gray-500">
								Appears as a main tab in the navigation (superadmin only)
							</p>
						</div>
					</div>

					<div className="flex justify-end space-x-3 mt-6">
						<button
							type="button"
							onClick={onClose}
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
							{page ? 'Update Page' : 'Create Page'}
						</button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default PageManagement;