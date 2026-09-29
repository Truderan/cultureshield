import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppShell } from "@/components/AppShell";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useAuth } from "@/App";
import { Users, UserPlus, Copy, CheckCircle, XCircle, Trash2, Mail, Loader2, Upload, Download, AlertCircle } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const FRONTEND_URL = window.location.origin;

const DEPARTMENTS = [
  "Engineering",
  "Marketing",
  "Sales",
  "Finance",
  "Human Resources",
  "Operations",
  "Customer Support",
  "Legal",
  "IT",
  "Other",
];

const EmployeeManagement = () => {
  const { user, token, logout } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showBulkImportDialog, setShowBulkImportDialog] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [bulkImportLoading, setBulkImportLoading] = useState(false);
  const [bulkImportResult, setBulkImportResult] = useState(null);
  const [newEmployee, setNewEmployee] = useState({
    name: "",
    email: "",
    department: "",
  });
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchEmployees();
  }, []);

  const fetchEmployees = async () => {
    try {
      const response = await fetch(`${API}/employees`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setEmployees(data);
      }
    } catch (error) {
      toast.error("Failed to load employees");
    } finally {
      setLoading(false);
    }
  };

  const handleAddEmployee = async () => {
    if (!newEmployee.name || !newEmployee.email || !newEmployee.department) {
      toast.error("Please fill in all fields");
      return;
    }

    setAddLoading(true);
    try {
      const response = await fetch(`${API}/employees`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newEmployee),
      });

      if (response.ok) {
        const data = await response.json();
        setEmployees((prev) => [...prev, data]);
        setNewEmployee({ name: "", email: "", department: "" });
        setShowAddDialog(false);
        toast.success("Employee added successfully!");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to add employee");
      }
    } catch (error) {
      toast.error("Connection error");
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeleteEmployee = async (employeeId) => {
    if (!window.confirm("Are you sure you want to delete this employee?")) return;

    try {
      const response = await fetch(`${API}/employees/${employeeId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setEmployees((prev) => prev.filter((e) => e.id !== employeeId));
        toast.success("Employee deleted");
      } else {
        toast.error("Failed to delete employee");
      }
    } catch (error) {
      toast.error("Connection error");
    }
  };

  const copyLink = (surveyLink) => {
    const fullLink = `${FRONTEND_URL}${surveyLink}`;
    navigator.clipboard.writeText(fullLink);
    toast.success("Survey link copied to clipboard!");
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      toast.error("Please upload a CSV file");
      return;
    }

    setBulkImportLoading(true);
    setBulkImportResult(null);

    try {
      const text = await file.text();
      const lines = text.split('\n').filter(line => line.trim());
      
      if (lines.length < 2) {
        toast.error("CSV file must have a header row and at least one data row");
        setBulkImportLoading(false);
        return;
      }

      // Parse header
      const header = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/["']/g, ''));
      const nameIdx = header.findIndex(h => h === 'name' || h === 'full name' || h === 'employee name');
      const emailIdx = header.findIndex(h => h === 'email' || h === 'email address');
      const deptIdx = header.findIndex(h => h === 'department' || h === 'dept');

      if (nameIdx === -1 || emailIdx === -1) {
        toast.error("CSV must have 'name' and 'email' columns");
        setBulkImportLoading(false);
        return;
      }

      // Parse data rows
      const employees = [];
      for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length > Math.max(nameIdx, emailIdx)) {
          employees.push({
            name: values[nameIdx]?.trim().replace(/["']/g, '') || '',
            email: values[emailIdx]?.trim().replace(/["']/g, '') || '',
            department: deptIdx !== -1 ? values[deptIdx]?.trim().replace(/["']/g, '') || 'Unassigned' : 'Unassigned'
          });
        }
      }

      if (employees.length === 0) {
        toast.error("No valid employee data found in CSV");
        setBulkImportLoading(false);
        return;
      }

      // Send to API
      const response = await fetch(`${API}/employees/bulk-import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ employees }),
      });

      if (response.ok) {
        const result = await response.json();
        setBulkImportResult(result);
        
        if (result.successful > 0) {
          setEmployees((prev) => [...prev, ...result.employees_created]);
          toast.success(`Successfully imported ${result.successful} employees!`);
        }
        
        if (result.failed > 0) {
          toast.warning(`${result.failed} employees failed to import. Check errors below.`);
        }
      } else {
        const error = await response.json();
        toast.error(error.detail || "Bulk import failed");
      }
    } catch (error) {
      toast.error("Failed to process CSV file");
    } finally {
      setBulkImportLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Helper function to parse CSV line (handles quoted values)
  const parseCSVLine = (line) => {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"' && (i === 0 || line[i-1] !== '\\')) {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current);
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current);
    
    return result;
  };

  const downloadTemplate = () => {
    const csvContent = "name,email,department\nJohn Doe,john.doe@company.com,Engineering\nJane Smith,jane.smith@company.com,Marketing\nBob Wilson,bob.wilson@company.com,Finance";
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employee_import_template.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    toast.success("Template downloaded!");
  };

  const completedCount = employees.filter((e) => e.survey_completed).length;
  const pendingCount = employees.filter((e) => !e.survey_completed).length;

  return (
    <AppShell current="employees" testId="employee-management-main">
{/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#18181B] ">
              Employee Management
            </h1>
            <p className="text-zinc-600 mt-1">
              Invite employees and track survey participation
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Bulk Import Dialog */}
            <Dialog open={showBulkImportDialog} onOpenChange={setShowBulkImportDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" className="border-[#18181B] text-[#18181B] hover:bg-[#18181B] hover:text-white" data-testid="bulk-import-btn">
                  <Upload className="w-4 h-4 mr-2" />
                  Bulk Import
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-[#18181B] ">
                    Bulk Import Employees
                  </DialogTitle>
                  <DialogDescription className="sr-only">
                    Upload a CSV file to create multiple employees and send survey invitations in one step.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div className="bg-zinc-50 p-4 rounded-lg">
                    <p className="text-sm text-zinc-600 mb-3">
                      Upload a CSV file with employee data. Required columns: <strong>name</strong>, <strong>email</strong>. Optional: <strong>department</strong>.
                    </p>
                    <Button variant="outline" size="sm" onClick={downloadTemplate} className="text-[#00A8E8]">
                      <Download className="w-4 h-4 mr-2" />
                      Download Template
                    </Button>
                  </div>

                  <div className="border-2 border-dashed border-zinc-300 rounded-lg p-8 text-center hover:border-[#00A8E8] transition-colors">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="csv-upload"
                      data-testid="csv-file-input"
                    />
                    <label htmlFor="csv-upload" className="cursor-pointer">
                      <Upload className="w-10 h-10 mx-auto mb-3 text-zinc-400" />
                      <p className="text-zinc-600 mb-1">Click to upload CSV file</p>
                      <p className="text-xs text-zinc-500">Maximum 500 employees per import</p>
                    </label>
                  </div>

                  {bulkImportLoading && (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="w-6 h-6 animate-spin text-[#00A8E8] mr-2" />
                      <span className="text-zinc-600">Processing CSV...</span>
                    </div>
                  )}

                  {bulkImportResult && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-3 gap-3">
                        <div className="bg-zinc-50 p-3 rounded-lg text-center">
                          <p className="text-2xl font-bold text-zinc-700">{bulkImportResult.total_processed}</p>
                          <p className="text-xs text-zinc-500">Total</p>
                        </div>
                        <div className="bg-green-50 p-3 rounded-lg text-center">
                          <p className="text-2xl font-bold text-green-600">{bulkImportResult.successful}</p>
                          <p className="text-xs text-zinc-500">Success</p>
                        </div>
                        <div className="bg-red-50 p-3 rounded-lg text-center">
                          <p className="text-2xl font-bold text-red-600">{bulkImportResult.failed}</p>
                          <p className="text-xs text-zinc-500">Failed</p>
                        </div>
                      </div>

                      {bulkImportResult.errors.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 max-h-40 overflow-y-auto">
                          <p className="text-sm font-medium text-red-700 mb-2 flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            Import Errors
                          </p>
                          <ul className="text-xs text-red-600 space-y-1">
                            {bulkImportResult.errors.slice(0, 10).map((err, idx) => (
                              <li key={idx}>Row {err.row}: {err.error}</li>
                            ))}
                            {bulkImportResult.errors.length > 10 && (
                              <li>... and {bulkImportResult.errors.length - 10} more errors</li>
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </DialogContent>
            </Dialog>

            {/* Add Single Employee Dialog */}
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button className="bg-[#00A8E8] hover:bg-[#008dc2] text-white" data-testid="add-employee-btn">
                  <UserPlus className="w-4 h-4 mr-2" />
                  Add Employee
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-[#18181B] ">
                    Add New Employee
                  </DialogTitle>
                  <DialogDescription className="sr-only">
                    Add one employee with their name, email, and department to generate a survey invitation.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label>Full Name</Label>
                    <Input
                      placeholder="John Doe"
                      value={newEmployee.name}
                      onChange={(e) =>
                        setNewEmployee((prev) => ({ ...prev, name: e.target.value }))
                      }
                      data-testid="employee-name-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email Address</Label>
                    <Input
                      type="email"
                      placeholder="john@company.com"
                      value={newEmployee.email}
                      onChange={(e) =>
                        setNewEmployee((prev) => ({ ...prev, email: e.target.value }))
                      }
                      data-testid="employee-email-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Department</Label>
                    <Select
                      value={newEmployee.department}
                      onValueChange={(value) =>
                        setNewEmployee((prev) => ({ ...prev, department: value }))
                      }
                    >
                      <SelectTrigger data-testid="employee-department-select">
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        {DEPARTMENTS.map((dept) => (
                          <SelectItem key={dept} value={dept}>
                            {dept}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                  className="w-full bg-[#18181B] hover:bg-[#000000]"
                  onClick={handleAddEmployee}
                  disabled={addLoading}
                  data-testid="submit-employee-btn"
                >
                  {addLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <UserPlus className="w-4 h-4 mr-2" />
                      Add Employee
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Total Employees</p>
                  <p className="text-3xl font-bold text-[#18181B] ">
                    {employees.length}
                  </p>
                </div>
                <div className="w-12 h-12 bg-[#18181B]/10 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-[#18181B]" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Completed Surveys</p>
                  <p className="text-3xl font-bold text-[#2ECC71] ">
                    {completedCount}
                  </p>
                </div>
                <div className="w-12 h-12 bg-[#2ECC71]/10 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-[#2ECC71]" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Pending Surveys</p>
                  <p className="text-3xl font-bold text-[#F39C12] ">
                    {pendingCount}
                  </p>
                </div>
                <div className="w-12 h-12 bg-[#F39C12]/10 rounded-lg flex items-center justify-center">
                  <Mail className="w-6 h-6 text-[#F39C12]" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Employee Table */}
        <Card className="dashboard-card">
          <CardHeader>
            <CardTitle className="text-[#18181B] ">
              Employee List
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-[#00A8E8]" />
              </div>
            ) : employees.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
                <p className="text-zinc-500 mb-4">No employees added yet</p>
                <Button
                  onClick={() => setShowAddDialog(true)}
                  className="bg-[#00A8E8] hover:bg-[#008dc2]"
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  Add Your First Employee
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Department</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Survey Link</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {employees.map((employee) => (
                    <TableRow key={employee.id} data-testid={`employee-row-${employee.id}`}>
                      <TableCell className="font-medium">{employee.name}</TableCell>
                      <TableCell className="text-zinc-600">{employee.email}</TableCell>
                      <TableCell>
                        <span className="px-2 py-1 bg-zinc-100 rounded text-sm">
                          {employee.department}
                        </span>
                      </TableCell>
                      <TableCell>
                        {employee.survey_completed ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                            <CheckCircle className="w-3 h-3" />
                            Completed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 rounded text-sm">
                            <XCircle className="w-3 h-3" />
                            Pending
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyLink(employee.survey_link)}
                          className="text-[#00A8E8] hover:text-[#008dc2]"
                          data-testid={`copy-link-${employee.id}`}
                        >
                          <Copy className="w-4 h-4 mr-1" />
                          Copy Link
                        </Button>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteEmployee(employee.id)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50"
                          data-testid={`delete-employee-${employee.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </AppShell>
  );
};

export default EmployeeManagement;
