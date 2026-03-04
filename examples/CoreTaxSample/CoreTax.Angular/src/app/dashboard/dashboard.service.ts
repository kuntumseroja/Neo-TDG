import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface DashboardSummary {
  totalRegistrations: number;
  totalInvoices: number;
  totalFilings: number;
  totalPayments: number;
  totalTaxDue: number;
  totalTaxPaid: number;
  outstandingBalance: number;
  period: string;
}

export interface TaxObligationSummary {
  obligationId: string;
  taxType: string;
  filingType: string;
  dueDate: string;
  status: string;
  amount: number;
  isPastDue: boolean;
}

export interface RecentActivity {
  activityId: string;
  activityType: string;
  description: string;
  timestamp: string;
  referenceId: string;
  status: string;
}

export interface ComplianceStatus {
  npwp: string;
  complianceScore: number;
  filingComplianceRate: number;
  paymentComplianceRate: number;
  lastAssessmentDate: string;
  penalties: number;
  status: string;
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/dashboard`;

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  /**
   * Retrieve the dashboard summary including totals for registrations, invoices, filings, and payments.
   * GET /api/v1/dashboard/summary
   */
  getDashboardSummary(period?: string): Observable<DashboardSummary> {
    let httpParams = new HttpParams();
    if (period) {
      httpParams = httpParams.set('period', period);
    }

    return this.http.get<DashboardSummary>(
      `${this.apiUrl}/summary`,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve outstanding tax obligations and their due dates.
   * GET /api/v1/dashboard/obligations
   */
  getTaxObligations(params?: { status?: string; taxType?: string }): Observable<TaxObligationSummary[]> {
    let httpParams = new HttpParams();
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.taxType) {
      httpParams = httpParams.set('taxType', params.taxType);
    }

    return this.http.get<TaxObligationSummary[]>(
      `${this.apiUrl}/obligations`,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve the most recent activities across all modules.
   * GET /api/v1/dashboard/activities
   */
  getRecentActivities(limit?: number): Observable<RecentActivity[]> {
    let httpParams = new HttpParams();
    if (limit) {
      httpParams = httpParams.set('limit', limit.toString());
    }

    return this.http.get<RecentActivity[]>(
      `${this.apiUrl}/activities`,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve the taxpayer compliance status and score.
   * GET /api/v1/dashboard/compliance
   */
  getComplianceStatus(): Observable<ComplianceStatus> {
    return this.http.get<ComplianceStatus>(
      `${this.apiUrl}/compliance`,
      this.httpOptions
    );
  }

  /**
   * Retrieve tax payment statistics grouped by type or period.
   * GET /api/v1/dashboard/statistics
   */
  getPaymentStatistics(groupBy?: string, period?: string): Observable<any> {
    let httpParams = new HttpParams();
    if (groupBy) {
      httpParams = httpParams.set('groupBy', groupBy);
    }
    if (period) {
      httpParams = httpParams.set('period', period);
    }

    return this.http.get(
      `${this.apiUrl}/statistics`,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve notifications and alerts for the taxpayer.
   * GET /api/v1/dashboard/notifications
   */
  getNotifications(): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.apiUrl}/notifications`,
      this.httpOptions
    );
  }
}
