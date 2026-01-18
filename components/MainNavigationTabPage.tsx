import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Dashboard from './Dashboard';

interface MainNavigationTabPageProps {
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
	isMainTab: boolean;
	isBuiltin: boolean;
	createdBy: number;
	createdAt: string;
	updatedAt: string;
}

const MainNavigationTabPage: React.FC<MainNavigationTabPageProps> = ({ isDark, user }) => {
	const location = useLocation();
	const [pageData, setPageData] = useState<PageData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		loadPageData();
	}, [location.pathname]);

	const loadPageData = async () => {
		try {
			setLoading(true);
			// Get all pages and find the one matching the current route
			const response = await fetch('/api/admin/pages', {
				credentials: 'include',
			});

			if (!response.ok) {
				throw new Error('Failed to load pages');
			}

			const pages = await response.json();
			const currentPage = pages.find((page: PageData) => page.route === location.pathname);

			if (!currentPage) {
				throw new Error('Page not found');
			}

			setPageData(currentPage);
		} catch (err) {
			setError(err instanceof Error ? err.message : 'An error occurred');
		} finally {
			setLoading(false);
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

	// Use Dashboard component with page-specific data
	return (
		<Dashboard
			isDark={isDark}
			user={user}
			customTitle={pageData.title}
			customDescription={pageData.description}
			isCustom={true}
			pageId={pageData.id}
		/>
	);
};

export default MainNavigationTabPage;