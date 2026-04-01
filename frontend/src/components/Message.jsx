import { IconAlertCircle, IconCheck, IconX } from "@tabler/icons-react";

export const SuccessMessage = ({ successMessage }) => {
  return (
    <div className="fixed top-4 right-4 z-50">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 shadow-lg flex items-center gap-3 animate-slide-in">
        <IconCheck className="w-5 h-5 text-green-600" />
        <span className="text-green-800 font-medium">{successMessage}</span>
      </div>
    </div>
  );
};
export const ErrorMessage = ({ errorMessage, setShowError }) => {
  return (
    <div className="fixed top-4 right-4 z-50">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg flex items-center justify-between animate-slide-in max-w-md">
        <div className="flex items-center gap-3">
          <IconAlertCircle className="w-5 h-5 text-red-600" />
          <span className="text-red-800">{errorMessage}</span>
        </div>
        <button
          onClick={() => setShowError("")}
          className="text-red-600 hover:text-red-800"
        >
          <IconX className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
