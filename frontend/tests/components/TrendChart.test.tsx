import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  TrendChart,
  BaseLineChart,
  formatChartDate,
  formatChartNumber,
  formatChartBytes,
  formatChartPercent,
  CHART_COLORS,
  METRIC_COLORS
} from '@/components/trends/TrendChart'

// Mock recharts to avoid canvas/SVG issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children, data }: { children: React.ReactNode; data: any[] }) => (
    <div data-testid="line-chart" data-point-count={data?.length ?? 0}>
      {children}
    </div>
  ),
  Line: ({ dataKey, name, stroke }: { dataKey: string; name: string; stroke: string }) => (
    <div data-testid={`line-${dataKey}`} data-name={name} data-stroke={stroke} />
  ),
  XAxis: ({ dataKey }: { dataKey: string }) => <div data-testid="x-axis" data-key={dataKey} />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}))

// ============================================================================
// TrendChart Wrapper Tests
// ============================================================================

describe('TrendChart', () => {
  it('should render title and description', () => {
    render(
      <TrendChart title="Test Chart" description="Test description">
        <div>Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('Test Chart')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('should render title without description', () => {
    render(
      <TrendChart title="Test Chart">
        <div>Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('Test Chart')).toBeInTheDocument()
  })

  it('should show loading spinner when loading is true', () => {
    render(
      <TrendChart title="Test Chart" loading={true}>
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    // Loading spinner should be visible (via animate-spin class)
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()

    // Content should not be visible
    expect(screen.queryByTestId('chart-content')).not.toBeInTheDocument()
  })

  it('should show error message when error is provided', () => {
    render(
      <TrendChart title="Test Chart" error="Something went wrong">
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.queryByTestId('chart-content')).not.toBeInTheDocument()
  })

  it('should show empty message when isEmpty is true', () => {
    render(
      <TrendChart title="Test Chart" isEmpty={true} emptyMessage="No data available">
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('No data available')).toBeInTheDocument()
    expect(screen.queryByTestId('chart-content')).not.toBeInTheDocument()
  })

  it('should show default empty message when isEmpty is true without custom message', () => {
    render(
      <TrendChart title="Test Chart" isEmpty={true}>
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('No trend data available')).toBeInTheDocument()
  })

  it('should render children when not loading/error/empty', () => {
    render(
      <TrendChart title="Test Chart">
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    expect(screen.getByTestId('chart-content')).toBeInTheDocument()
    expect(screen.getByText('Chart content')).toBeInTheDocument()
  })

  it('should prioritize loading over error and empty states', () => {
    render(
      <TrendChart title="Test Chart" loading={true} error="Error" isEmpty={true}>
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    // Should show loading spinner, not error or empty
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(screen.queryByText('Error')).not.toBeInTheDocument()
  })

  it('should prioritize error over empty state', () => {
    render(
      <TrendChart title="Test Chart" error="Error message" isEmpty={true}>
        <div data-testid="chart-content">Chart content</div>
      </TrendChart>
    )

    expect(screen.getByText('Error message')).toBeInTheDocument()
    expect(screen.queryByText('No trend data available')).not.toBeInTheDocument()
  })
})

// ============================================================================
// BaseLineChart Tests
// ============================================================================

describe('BaseLineChart', () => {
  const mockData = [
    { date: '2025-01-01', value1: 10, value2: 20 },
    { date: '2025-01-02', value1: 15, value2: 25 },
    { date: '2025-01-03', value1: 12, value2: 22 },
  ]

  const mockLines = [
    { dataKey: 'value1', name: 'Value 1', color: '#ff0000' },
    { dataKey: 'value2', name: 'Value 2', color: '#00ff00' },
  ]

  it('should render ResponsiveContainer', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('should render LineChart with data', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    const lineChart = screen.getByTestId('line-chart')
    expect(lineChart).toBeInTheDocument()
    expect(lineChart).toHaveAttribute('data-point-count', '3')
  })

  it('should render correct number of Line elements', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    expect(screen.getByTestId('line-value1')).toBeInTheDocument()
    expect(screen.getByTestId('line-value2')).toBeInTheDocument()
  })

  it('should pass correct props to Line elements', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    const line1 = screen.getByTestId('line-value1')
    expect(line1).toHaveAttribute('data-name', 'Value 1')
    expect(line1).toHaveAttribute('data-stroke', '#ff0000')

    const line2 = screen.getByTestId('line-value2')
    expect(line2).toHaveAttribute('data-name', 'Value 2')
    expect(line2).toHaveAttribute('data-stroke', '#00ff00')
  })

  it('should render XAxis with correct dataKey', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    const xAxis = screen.getByTestId('x-axis')
    expect(xAxis).toHaveAttribute('data-key', 'date')
  })

  it('should render YAxis, CartesianGrid, Tooltip, and Legend', () => {
    render(
      <BaseLineChart data={mockData} xDataKey="date" lines={mockLines} />
    )

    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
    expect(screen.getByTestId('legend')).toBeInTheDocument()
  })
})

// ============================================================================
// Utility Function Tests
// ============================================================================

describe('formatChartDate', () => {
  it('should format date in short format', () => {
    // Use a date that's timezone-safe (mid-month)
    const result = formatChartDate('2025-01-15T12:00:00Z')
    // Short format: "1/15/25" (US) or similar locale-dependent format
    expect(result).toMatch(/1.*15|15.*1/) // Contains month and day
    expect(result).toMatch(/25/) // Contains year
  })

  it('should handle ISO timestamp strings', () => {
    const result = formatChartDate('2025-06-15T10:30:00Z')
    // Short format: "6/15/25" (US) or similar
    expect(result).toMatch(/6.*15|15.*6/) // Contains month and day
    expect(result).toMatch(/25/) // Contains year
  })
})

describe('formatChartNumber', () => {
  it('should format small numbers as-is', () => {
    expect(formatChartNumber(0)).toBe('0')
    expect(formatChartNumber(100)).toBe('100')
    expect(formatChartNumber(999)).toBe('999')
  })

  it('should format thousands with K suffix', () => {
    expect(formatChartNumber(1000)).toBe('1.0K')
    expect(formatChartNumber(1500)).toBe('1.5K')
    expect(formatChartNumber(10000)).toBe('10.0K')
    expect(formatChartNumber(999999)).toBe('1000.0K')
  })

  it('should format millions with M suffix', () => {
    expect(formatChartNumber(1000000)).toBe('1.0M')
    expect(formatChartNumber(1500000)).toBe('1.5M')
    expect(formatChartNumber(10000000)).toBe('10.0M')
  })
})

describe('formatChartBytes', () => {
  it('should format bytes as-is for small values', () => {
    expect(formatChartBytes(0)).toBe('0 B')
    expect(formatChartBytes(500)).toBe('500 B')
    expect(formatChartBytes(1023)).toBe('1023 B')
  })

  it('should format kilobytes with KB suffix', () => {
    expect(formatChartBytes(1024)).toBe('1.0 KB')
    expect(formatChartBytes(1536)).toBe('1.5 KB')
    expect(formatChartBytes(10240)).toBe('10.0 KB')
  })

  it('should format megabytes with MB suffix', () => {
    expect(formatChartBytes(1048576)).toBe('1.0 MB')
    expect(formatChartBytes(1572864)).toBe('1.5 MB')
    expect(formatChartBytes(10485760)).toBe('10.0 MB')
  })

  it('should format gigabytes with GB suffix', () => {
    expect(formatChartBytes(1073741824)).toBe('1.0 GB')
    expect(formatChartBytes(1610612736)).toBe('1.5 GB')
    expect(formatChartBytes(5368709120)).toBe('5.0 GB')
  })
})

describe('formatChartPercent', () => {
  it('should format percentage with % suffix', () => {
    expect(formatChartPercent(0)).toBe('0.0%')
    expect(formatChartPercent(50)).toBe('50.0%')
    expect(formatChartPercent(100)).toBe('100.0%')
  })

  it('should format decimal percentages', () => {
    expect(formatChartPercent(33.33)).toBe('33.3%')
    expect(formatChartPercent(66.666)).toBe('66.7%')
    expect(formatChartPercent(99.99)).toBe('100.0%')
  })
})

// ============================================================================
// Color Constants Tests
// ============================================================================

describe('CHART_COLORS', () => {
  it('should have 5 chart colors', () => {
    expect(CHART_COLORS).toHaveLength(5)
  })

  it('should use CSS variables for theme consistency', () => {
    CHART_COLORS.forEach((color) => {
      expect(color).toContain('hsl(var(--chart-')
    })
  })
})

describe('METRIC_COLORS', () => {
  it('should have semantic color keys', () => {
    expect(METRIC_COLORS).toHaveProperty('success')
    expect(METRIC_COLORS).toHaveProperty('warning')
    expect(METRIC_COLORS).toHaveProperty('destructive')
    expect(METRIC_COLORS).toHaveProperty('muted')
  })

  it('should use CSS variables', () => {
    expect(METRIC_COLORS.success).toContain('hsl(var(--')
    expect(METRIC_COLORS.warning).toContain('hsl(var(--')
    expect(METRIC_COLORS.destructive).toContain('hsl(var(--')
    expect(METRIC_COLORS.muted).toContain('hsl(var(--')
  })
})
