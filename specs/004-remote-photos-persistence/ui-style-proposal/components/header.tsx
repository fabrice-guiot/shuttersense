export function Header() {
  return (
    <header className="bg-[#4A90E2] text-white">
      <div className="flex items-center justify-between px-6 py-4">
        <h1 className="text-xl font-medium">Photo Admin</h1>
        <div className="flex items-center gap-6">
          <button className="flex items-center gap-2 hover:opacity-90">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.5a2 2 0 00-1 .267M7 21h10a2 2 0 002-2v-4a2 2 0 00-2-2h-2.5a2 2 0 00-1 .267"
              />
            </svg>
            <span className="text-sm font-medium">CONNECTORS</span>
          </button>
          <button className="flex items-center gap-2 hover:opacity-90">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span className="text-sm font-medium">COLLECTIONS</span>
          </button>
        </div>
      </div>
    </header>
  )
}
