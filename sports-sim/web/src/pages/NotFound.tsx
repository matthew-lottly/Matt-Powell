export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h1 className="text-6xl font-bold text-white/80 mb-4">404</h1>
      <p className="text-xl text-white/60 mb-6">Page not found</p>
      <a
        href="/"
        className="px-6 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
      >
        Back to Home
      </a>
    </div>
  );
}
