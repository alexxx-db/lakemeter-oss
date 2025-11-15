"use client";

import { useState } from "react";

export default function Home() {
  // State for the large text input
  const [promptText, setPromptText] = useState("");
  
  // State for table data - starts with no rows
  const [tableData, setTableData] = useState<Array<Array<{type: string, value: string}>>>([]);

  const handleTableChange = (rowIndex: number, colIndex: number, value: string) => {
    const newData = [...tableData];
    newData[rowIndex][colIndex].value = value;
    setTableData(newData);
  };

  const addRow = () => {
    const newRow = [
      { type: "dropdown", value: "Ingestion" },
      { type: "dropdown", value: "All-Purpose" },
      { type: "dropdown", value: "i3.xlarge" },
      { type: "dropdown", value: "1" },
      { type: "dropdown", value: "i3.xlarge" },
      { type: "dropdown", value: "1" },
      { type: "text", value: "" },
      { type: "text", value: "" },
    ];
    setTableData([...tableData, newRow]);
  };

  const removeRow = (rowIndex: number) => {
    if (tableData.length > 1) {
      const newData = tableData.filter((_, index) => index !== rowIndex);
      setTableData(newData);
    }
  };

  // Define dropdown options for each column
  const workloadOptions = ["Ingestion", "Transformation", "Analysis", "Exploration", "ML Inference"];
  const skuOptions = ["All-Purpose", "SQL Pro", "Jobs", "Serverless"];
  const driverInstanceOptions = ["i3.xlarge", "i3.2xlarge", "i3.4xlarge"];
  const driverCountOptions = ["1"];
  const workerInstanceOptions = ["i3.xlarge", "i3.2xlarge", "i3.4xlarge"];
  const workerCountOptions = Array.from({ length: 20 }, (_, i) => String(i + 1));

  // Function to get dropdown options based on column index
  const getDropdownOptions = (colIndex: number) => {
    switch (colIndex) {
      case 0:
        return workloadOptions;
      case 1:
        return skuOptions;
      case 2:
        return driverInstanceOptions;
      case 3:
        return driverCountOptions;
      case 4:
        return workerInstanceOptions;
      case 5:
        return workerCountOptions;
      default:
        return [];
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-8">
          Prompt Input & Data Table
        </h1>

        {/* Large Text Input Field */}
        <div className="mb-8">
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Enter Your Prompt
          </label>
          <textarea
            id="prompt"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Type your prompt here..."
            className="w-full min-h-[200px] p-4 text-base border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-gray-100 resize-y transition-all"
            rows={8}
          />
          <button
            onClick={addRow}
            className="mt-4 px-6 py-2 text-base font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            Submit
          </button>
        </div>

        {/* Table with 8 columns and dynamic rows */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100 dark:bg-gray-700">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Workload
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    SKU
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Driver Instance
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Driver Count
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Worker Instance
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Worker Count
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Run Duration
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Run Frequency
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    {row.map((cell, colIndex) => (
                      <td
                        key={colIndex}
                        className="px-4 py-3 border-b dark:border-gray-600"
                      >
                        {cell.type === "text" ? (
                          <input
                            type="text"
                            value={cell.value}
                            onChange={(e) =>
                              handleTableChange(rowIndex, colIndex, e.target.value)
                            }
                            placeholder="Enter text..."
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                          />
                        ) : (
                          <select
                            value={cell.value}
                            onChange={(e) =>
                              handleTableChange(rowIndex, colIndex, e.target.value)
                            }
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                          >
                            {getDropdownOptions(colIndex).map((option: string) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        )}
                      </td>
                    ))}
                    <td className="px-4 py-3 border-b dark:border-gray-600">
                      <button
                        onClick={() => removeRow(rowIndex)}
                        disabled={tableData.length === 1}
                        className="px-3 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Add Row Button */}
          <div className="p-4 bg-gray-50 dark:bg-gray-750 border-t dark:border-gray-600">
            <button
              onClick={addRow}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              + Add Row
            </button>
          </div>
        </div>

        {/* Display current values (for debugging/demo purposes) */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900 rounded-lg">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
            Current Values
          </h2>
          <div className="text-sm text-gray-700 dark:text-gray-300">
            <p className="mb-2">
              <strong>Prompt:</strong> {promptText || "(empty)"}
            </p>
            <p>
              <strong>Table Data:</strong>
            </p>
            <pre className="mt-2 p-2 bg-white dark:bg-gray-800 rounded overflow-auto text-xs">
              {JSON.stringify(tableData, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
