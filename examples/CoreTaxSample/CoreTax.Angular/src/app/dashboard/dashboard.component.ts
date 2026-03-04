import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject, forkJoin } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { DashboardService, DashboardSummary, TaxObligationSummary, RecentActivity, ComplianceStatus } from './dashboard.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  dashboardSummary: DashboardSummary | null = null;
  taxObligations: TaxObligationSummary[] = [];
  recentActivities: RecentActivity[] = [];
  complianceStatus: ComplianceStatus | null = null;
  isLoading = true;
  errorMessage: string | null = null;

  selectedPeriod: string = 'current_year';
  selectedNpwp: string = '';

  periods = [
    { value: 'current_month', label: 'Bulan Ini' },
    { value: 'current_quarter', label: 'Kuartal Ini' },
    { value: 'current_year', label: 'Tahun Ini' },
    { value: 'last_year', label: 'Tahun Lalu' }
  ];

  private destroy$ = new Subject<void>();

  constructor(private dashboardService: DashboardService) {}

  ngOnInit(): void {
    this.loadDashboardData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDashboardData(): void {
    this.isLoading = true;
    this.errorMessage = null;

    forkJoin({
      summary: this.dashboardService.getDashboardSummary(this.selectedPeriod),
      obligations: this.dashboardService.getTaxObligations(),
      activities: this.dashboardService.getRecentActivities(10),
      compliance: this.dashboardService.getComplianceStatus()
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (results) => {
          this.dashboardSummary = results.summary;
          this.taxObligations = results.obligations;
          this.recentActivities = results.activities;
          this.complianceStatus = results.compliance;
          this.isLoading = false;
        },
        error: (error) => {
          this.errorMessage = error.error?.message || 'Failed to load dashboard data. Please refresh the page.';
          this.isLoading = false;
        }
      });
  }

  onPeriodChange(period: string): void {
    this.selectedPeriod = period;
    this.loadDashboardData();
  }

  getComplianceColor(): string {
    if (!this.complianceStatus) return 'gray';
    const score = this.complianceStatus.complianceScore;
    if (score >= 80) return 'green';
    if (score >= 60) return 'orange';
    return 'red';
  }

  getComplianceLabel(): string {
    if (!this.complianceStatus) return 'Unknown';
    const score = this.complianceStatus.complianceScore;
    if (score >= 80) return 'Patuh';
    if (score >= 60) return 'Cukup Patuh';
    return 'Tidak Patuh';
  }

  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0
    }).format(amount);
  }

  getActivityIcon(activityType: string): string {
    switch (activityType) {
      case 'REGISTRATION': return 'person_add';
      case 'INVOICE': return 'receipt';
      case 'FILING': return 'description';
      case 'PAYMENT': return 'payment';
      default: return 'info';
    }
  }

  refreshDashboard(): void {
    this.loadDashboardData();
  }
}
