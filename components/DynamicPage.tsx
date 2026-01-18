import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

interface DynamicPageProps {
	isDark: boolean;
	user?: { username: string; role: string } | null;
}

interface PageData {
	id: number;
	title: string;
	description: string;
	route: string;
	icon: string;
	isActive: boolean;
	isBuiltin: boolean;
	createdBy: number;
	createdAt: string;
	updatedAt: string;
}

const DynamicPage: React.FC<DynamicPageProps> = ({ isDark, user }) => {
	const { pageId } = useParams<{ pageId: string }>();
	const [pageData, setPageData] = useState<PageData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [showModifyModal, setShowModifyModal] = useState(false);

	useEffect(() => {
		loadPageData();
	}, [pageId]);

	const loadPageData = async () => {
		try {
			setLoading(true);
			const response = await fetch(`/api/admin/pages/${pageId}`, {
				credentials: 'include',
			});

			if (!response.ok) {
				throw new Error('Failed to load page data');
			}

			const data = await response.json();
			setPageData(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : 'An error occurred');
		} finally {
			setLoading(false);
		}
	};

	const handleModify = () => {
		setShowModifyModal(true);
	};

	const handleSaveChanges = async (updatedData: Partial<PageData>) => {
		try {
			const response = await fetch(`/api/admin/pages/${pageId}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
				},
				credentials: 'include',
				body: JSON.stringify(updatedData),
			});

			if (!response.ok) {
				throw new Error('Failed to update page');
			}

			const updatedPage = await response.json();
			setPageData(updatedPage);
			setShowModifyModal(false);
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Failed to update page');
		}
	};

	if (loading) {
		return (
			<div className={`flex items-center justify-center min-h-64 ${isDark ? 'text-white' : 'text-black'}`}>
				<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
			</div>
		);
	}

	if (error || !pageData) {
		return (
			<div className={`p-6 ${isDark ? 'text-white' : 'text-black'}`}>
				<div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
					{error || 'Page not found'}
				</div>
			</div>
		);
	}

	return (
		<div className={`p-6 ${isDark ? 'text-white' : 'text-black'}`}>
			{/* Page Header */}
			<div className="flex items-center justify-between mb-6">
				<div>
					<h1 className="text-3xl font-bold">{pageData.title}</h1>
					{pageData.description && (
						<p className={`mt-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
							{pageData.description}
						</p>
					)}
				</div>

				{/* Modify Button - Only for super_admin */}
				{user?.role === 'super_admin' && (
					<button
						onClick={handleModify}
						className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
					>
						Modify Page
					</button>
				)}
			</div>

			{/* Page Content */}
			<div className={`rounded-lg p-6 ${isDark ? 'bg-gray-800' : 'bg-gray-50'}`}>
				<div className="text-center py-12">
					<div className={`text-6xl mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
						📄
					</div>
					<h2 className="text-xl font-semibold mb-2">Page Content</h2>
					<p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
						This is a dynamic page. Content can be customized by the administrator.
					</p>
				</div>
			</div>

			{/* Modify Modal */}
			{showModifyModal && (
				<ModifyPageModal
					pageData={pageData}
					isDark={isDark}
					onSave={handleSaveChanges}
					onClose={() => setShowModifyModal(false)}
				/>
			)}
		</div>
	);
};

// Modify Page Modal Component
interface ModifyPageModalProps {
	pageData: PageData;
	isDark: boolean;
	onSave: (data: Partial<PageData>) => void;
	onClose: () => void;
}

const ModifyPageModal: React.FC<ModifyPageModalProps> = ({
	pageData,
	isDark,
	onSave,
	onClose
}) => {
	const [formData, setFormData] = useState({
		title: pageData.title,
		description: pageData.description || '',
		route: pageData.route,
		icon: pageData.icon,
		isActive: pageData.isActive,
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
				<h2 className="text-xl font-bold mb-4">Modify Page</h2>

				<form onSubmit={handleSubmit}>
					<div className="space-y-4">
						<div>
							<label className="block text-sm font-medium mb-1">Title</label>
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
							<label className="block text-sm font-medium mb-1">Route</label>
							<input
								type="text"
								value={formData.route}
								onChange={(e) => handleChange('route', e.target.value)}
								className={`w-full px-3 py-2 border rounded-lg ${isDark
										? 'bg-gray-700 border-gray-600 text-white'
										: 'bg-white border-gray-300 text-black'
									}`}
								required
							/>
						</div>

						<div>
							<label className="block text-sm font-medium mb-1">Icon</label>
							<input
								type="text"
								value={formData.icon}
								onChange={(e) => handleChange('icon', e.target.value)}
								className={`w-full px-3 py-2 border rounded-lg ${isDark
										? 'bg-gray-700 border-gray-600 text-white'
										: 'bg-white border-gray-300 text-black'
									}`}
							/>
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
							Save Changes
						</button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default DynamicPage;