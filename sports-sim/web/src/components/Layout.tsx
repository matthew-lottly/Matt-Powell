import { Link, Outlet, useLocation } from 'react-router-dom';

const NAV = [
  { path: '/', label: 'Home' },
  { path: '/simulate', label: 'Simulate' },
  { path: '/history', label: 'History' },
  { path: '/tuning', label: 'Tuning' },
  { path: '/dashboard', label: 'Dashboard' },
];

export default function Layout() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      {/* ───── top nav ───── */}
      <header className="bg-gray-900 border-b border-gray-800 px-3 sm:px-6 py-3 flex items-center justify-between sm:justify-start gap-4 sm:gap-8">
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
      </header>

      {/* ───── content ───── */}
      <main className="flex-1 p-2 sm:p-4 lg:p-6">
        <Outlet />
      </main>

      {/* ───── footer ───── */}
      <footer className="text-center text-xs text-gray-600 py-3 border-t border-gray-800">
        Sports Sim &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
