"use client";

import { useState } from "react";

export default function Home() {
  // State for the large text input
  const [promptText, setPromptText] = useState("");
  
  // State for table data - 3 rows, 5 columns each
  const [tableData, setTableData] = useState([
    [
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
      { type: "text", value: "" },
    ],
    [
      { type: "dropdown", value: "Option 1" },
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
    ],
    [
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
      { type: "text", value: "" },
      { type: "text", value: "" },
      { type: "dropdown", value: "Option 1" },
    ],
  ]);

  const handleTableChange = (rowIndex: number, colIndex: number, value: string) => {
    const newData = [...tableData];
    newData[rowIndex][colIndex].value = value;
    setTableData(newData);
  };

  const dropdownOptions = ["Option 1", "Option 2", "Option 3", "Option 4"];

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
        </div>

        {/* Table with 5 columns and 3 rows */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100 dark:bg-gray-700">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Column 1
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Column 2
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Column 3
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Column 4
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 border-b dark:border-gray-600">
                    Column 5
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
                            {dropdownOptions.map((option) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
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
