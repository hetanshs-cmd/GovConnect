
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  HeartPulse,
  Sprout,
  Building2,
  Bell,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
  Shield,
  Users,
  FileText,
  Database,
  Globe,
  Truck,
  Home,
  Briefcase
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isMobile: boolean;
  isDark: boolean;
  onMobileClose?: () => void;
  user?: any;
  dynamicSections?: any[];
  pages?: any[];
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, setIsOpen, isMobile, isDark, onMobileClose, user, dynamicSections, pages }) => {
  const location = useLocation();

  // Icon mapping for dynamic sections
  const iconMap: { [key: string]: any } = {
    'Building2': Building2,
    'Users': Users,
    'FileText': FileText,
    'Database': Database,
    'Globe': Globe,
    'Truck': Truck,
    'Home': Home,
    'Briefcase': Briefcase,
    'HeartPulse': HeartPulse,
    'Sprout': Sprout,
    'Bell': Bell,
    'Activity': Activity,
    'Shield': Shield
  };

  const menuItems = [
    { id: 'home', path: '/', icon: LayoutDashboard, label: 'Home' },
    { id: 'healthcare', path: '/healthcare', icon: HeartPulse, label: 'Healthcare' },
    { id: 'agriculture', path: '/agriculture', icon: Sprout, label: 'Agriculture' },
    { id: 'alerts', path: '/alerts', icon: Bell, label: 'Alerts' },
    { id: 'system-health', path: '/system-health', icon: Activity, label: 'System Health' },
  ];

  // Add custom dashboard for super admin only
  if (user && user.role === 'super_admin') {
    menuItems.splice(5, 0, { id: 'custom-dashboard', path: '/custom-dashboard', icon: LayoutDashboard, label: 'Custom Dashboard' });
  }

  // Add hospital registration for healthcare admin, admin, and super admin only
  if (user && (user.role === 'healthcare_admin' || user.role === 'admin' || user.role === 'super_admin')) {
    menuItems.splice(2, 0, { id: 'hospital-registration', path: '/hospital-registration', icon: Building2, label: 'Register Hospital' });
  }

  // Add farmer registration for agriculture admin, admin, and super admin only
  if (user && (user.role === 'agriculture_admin' || user.role === 'admin' || user.role === 'super_admin')) {
    menuItems.splice(3, 0, { id: 'farmer-registration', path: '/farmer-registration', icon: Sprout, label: 'Register Farmer' });
  }

  // Add dynamic sections
  if (dynamicSections && dynamicSections.length > 0) {
    dynamicSections.forEach((section, index) => {
      const DynamicIcon = iconMap[section.icon] || Building2; // Default to Building2 if no icon or invalid
      menuItems.splice(4 + index, 0, {
        id: `dynamic-${section.id}`,
        path: section.path,
        icon: DynamicIcon,
        label: section.title
      });
    });
  }

  // Add dynamic pages as main navigation tabs (for superadmin only)
  if (pages && pages.length > 0) {
    const mainTabPages = pages.filter(page => page.isMainTab && user && user.role === 'super_admin');
    const sidebarPages = pages.filter(page => !page.isMainTab);

    // Add main navigation tabs after system health
    mainTabPages.forEach((page) => {
      const PageIcon = iconMap[page.icon] || FileText;
      menuItems.splice(5, 0, {
        id: `page-${page.id}`,
        path: page.route,
        icon: PageIcon,
        label: page.title
      });
    });

    // Add sidebar pages at the end
    sidebarPages.forEach((page) => {
      const PageIcon = iconMap[page.icon] || FileText;
      menuItems.push({
        id: `page-${page.id}`,
        path: page.route,
        icon: PageIcon,
        label: page.title
      });
    });
  }

  // Add admin menu item for admin and super_admin users
  if (user && (user.role === 'admin' || user.role === 'super_admin')) {
    menuItems.push({ id: 'admin', path: '/admin', icon: Shield, label: 'User Management' });
  }

  const sidebarClasses = `
    fixed top-0 left-0 h-full ${isDark ? 'bg-gray-800 border-r border-gray-700' : 'bg-gray-100 border-r border-gray-300'} 
    ${isMobile ? (isOpen ? 'translate-x-0 w-64' : '-translate-x-full w-64') : (isOpen ? 'w-64' : 'w-16')}
  `;

  return (
    <aside className={sidebarClasses}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className={`p-4 ${isDark ? 'border-b border-gray-700' : 'border-b border-gray-300'}`}>
          {(isOpen || isMobile) ? (
            <div className="flex items-center gap-3">
              <div className={`${isDark ? 'bg-gray-600' : 'bg-gray-400'} w-8 h-8 rounded flex items-center justify-center font-bold text-white`}>G</div>
              <span className={`font-bold text-lg ${isDark ? 'text-white' : 'text-black'}`}>GovConnect</span>
            </div>
          ) : (
            <div className={`${isDark ? 'bg-gray-600' : 'bg-gray-400'} w-8 h-8 mx-auto rounded flex items-center justify-center font-bold text-white`}>G</div>
          )}
          {isMobile && (
            <button onClick={() => setIsOpen(false)} className={`absolute top-4 right-4 ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-black'}`}>
              <X className="w-6 h-6" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2">
          {menuItems.map((item) => (
            <Link
              key={item.id}
              to={item.path}
              onClick={() => isMobile && onMobileClose && onMobileClose()}
              className={`w-full flex items-center gap-3 px-3 py-2 mb-1 rounded ${location.pathname === item.path
                ? `${isDark ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'}`
                : `${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-200'}`
                }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {(isOpen || isMobile) && <span className="text-sm">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Footer Actions */}
        <div className={`p-2 ${isDark ? 'border-t border-gray-700' : 'border-t border-gray-300'}`}>
          <Link
            to="/settings"
            onClick={() => isMobile && onMobileClose && onMobileClose()}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded ${location.pathname === '/settings'
              ? `${isDark ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'}`
              : `${isDark ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-200'}`
              }`}
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            {(isOpen || isMobile) && <span className="text-sm">Settings</span>}
          </Link>
          {!isMobile && (
            <button
              onClick={() => setIsOpen(!isOpen)}
              className={`w-full flex items-center justify-center p-2 mt-2 ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-black'}`}
            >
              {isOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
