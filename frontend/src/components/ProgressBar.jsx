// ProgressBar.jsx
import React from "react";
import { motion } from "framer-motion";

const ProgressBar = ({ progress, stats, status }) => {
  return (
    <div className="w-full space-y-4">
      {/* Main Progress */}
      <div className="relative">
        <div className="flex justify-between mb-2">
          <span className="text-sm font-medium text-purple-300">{status}</span>
          <span className="text-sm font-medium text-purple-300">
            {Math.round(progress)}%
          </span>
        </div>

        <div className="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-400">Nodes</div>
          <div className="text-lg font-semibold text-white">
            {stats.nodesExplored.toLocaleString()}
          </div>
        </div>

        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-400">Frontier</div>
          <div className="text-lg font-semibold text-white">
            {stats.maxFrontier.toLocaleString()}
          </div>
        </div>

        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-400">Time</div>
          <div className="text-lg font-semibold text-white">
            {stats.elapsedTime.toFixed(1)}s
          </div>
        </div>

        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-xs text-gray-400">Speed</div>
          <div className="text-lg font-semibold text-white">
            {stats.speed} n/s
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressBar;
