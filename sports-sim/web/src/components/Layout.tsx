import { Link, Outlet, useLocation } from 'react-router-dom';

const NAV = [
  { path: '/', label: 'Home' },
  { path: '/simulate', label: 'Simulate' },
  { path: '/history', label: 'History' },
];

export default function Layout() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      {/* ───── top nav ───── */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-8">
        <Link to="/" className="text-xl font-bold tracking-tight text-blue-400">
          Sports Sim
        </Link>
        <nav className="flex gap-4 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.path}
              to={n.path}
              className={`px-3 py-1 rounded-md transition ${
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
      <main className="flex-1 p-6">
        <Outlet />
      </main>

      {/* ───── footer ───── */}
      <footer className="text-center text-xs text-gray-600 py-3 border-t border-gray-800">
        Sports Sim &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
