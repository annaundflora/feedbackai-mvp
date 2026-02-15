import React from 'react'

export function ChatScreen() {
  return (
    <div className="flex flex-col h-full screen-container">
      {/* Placeholder für @assistant-ui Thread */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-8 h-8 text-gray-400"
              aria-hidden="true"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Chat bereit
          </h3>
          <p className="text-sm text-gray-600">
            @assistant-ui Integration kommt in Slice 4
          </p>
        </div>
      </div>

      {/* Placeholder für @assistant-ui Composer */}
      <div className="p-4 border-t border-gray-200">
        <div className="px-4 py-3 rounded-lg bg-gray-100 text-gray-500 text-sm">
          Nachricht eingeben...
        </div>
      </div>
    </div>
  )
}
