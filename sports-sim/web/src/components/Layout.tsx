import { Link, Outlet, useLocation } from 'react-router-dom';
import { useTheme } from '../ThemeContext';

const NAV = [
  { path: '/', label: 'Home' },
  { path: '/simulate', label: 'Simulate' },
  { path: '/leagues', label: 'Leagues' },
  { path: '/history', label: 'History' },
  { path: '/tuning', label: 'Tuning' },
  { path: '/dashboard', label: 'Dashboard' },
];

export default function Layout() {
  const { pathname } = useLocation();
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen flex flex-col">
      {/* ───── top nav ───── */}
      <header className="app-surface-1 app-border-surface-2 border-b px-3 sm:px-6 py-3 flex items-center justify-between sm:justify-start gap-4 sm:gap-8">
        <Link to="/" className="text-lg sm:text-xl font-bold tracking-tight text-blue-400 shrink-0">
          Sports Sim
        </Link>
        <nav className="flex gap-1 sm:gap-4 text-xs sm:text-sm overflow-x-auto">
          {NAV.map((n) => (
            <Link
              key={n.path}
              to={n.path}
              className={`px-2 sm:px-3 py-1 rounded-md transition whitespace-nowrap ${
                pathname === n.path
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <button
          onClick={toggle}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          className="ml-auto text-lg px-2 py-1 rounded-md hover:bg-gray-700 transition"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </header>

      {/* ───── content ───── */}
      <main className="flex-1 p-2 sm:p-4 lg:p-6">
        <Outlet />
      </main>

      {/* ───── footer ───── */}
      <footer className="app-copy-1 app-border-surface-2 text-center text-xs py-3 border-t">
        Sports Sim &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
