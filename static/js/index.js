window.app = Vue.createApp({
  el: '#dcaClient',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
      dashboardData: null,
      transactions: [],
      loading: true,
      error: null,
      showFiatValues: false,  // Hide fiat values by default
      transactionColumns: [
        {
          name: 'date',
          label: 'Date',
          align: 'left',
          field: row => row.transaction_time || row.created_at,
          sortable: false
        },
        {
          name: 'amount_sats',
          label: 'Bitcoin',
          align: 'right',
          field: 'amount_sats',
          sortable: false
        },
        {
          name: 'amount_fiat',
          label: 'Fiat Amount',
          align: 'right',
          field: 'amount_fiat',
          sortable: false
        },
        {
          name: 'type',
          label: 'Type',
          align: 'center',
          field: 'transaction_type',
          sortable: false
        },
        {
          name: 'status',
          label: 'Status',
          align: 'center',
          field: 'status',
          sortable: false
        }
      ],
      transactionPagination: {
        sortBy: 'date',
        descending: true,
        page: 1,
        rowsPerPage: 10
      },
      chartTimeRange: '30d',
      dcaChart: null,
      analyticsData: null
    }
  },

  methods: {
    formatCurrency(amount) {
      if (!amount) return 'Q 0.00';
      // Values are already in full currency units, not centavos
      return new Intl.NumberFormat('es-GT', {
        style: 'currency',
        currency: 'GTQ',
      }).format(amount);
    },

    formatCurrencyWithCode(amount, currencyCode) {
      if (!amount) return `${currencyCode} 0.00`;
      // Format with the provided currency code
      try {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: currencyCode,
        }).format(amount);
      } catch (error) {
        // Fallback if currency code is not supported
        return `${currencyCode} ${amount.toFixed(2)}`;
      }
    },

    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      if (isNaN(date.getTime())) {
        console.warn('Invalid date string:', dateString)
        return 'Invalid Date'
      }
      return date.toLocaleDateString()
    },

    formatTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      if (isNaN(date.getTime())) {
        console.warn('Invalid time string:', dateString)
        return 'Invalid Time'
      }
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    formatSats(amount) {
      if (!amount) return '0 sats'
      const formatted = new Intl.NumberFormat('en-US').format(amount)
      // Add some excitement for larger amounts
      if (amount >= 1000000) return formatted + ' sats 💎'
      if (amount >= 100000) return formatted + ' sats 🚀'
      if (amount >= 10000) return formatted + ' sats ⚡'
      return formatted + ' sats'
    },

    async loadDashboardData() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/satmachineclient/api/v1/dashboard/summary',
          this.g.user.wallets[0].inkey
        )
        this.dashboardData = data
      } catch (error) {
        console.error('Error loading dashboard data:', error)
        this.error = 'Failed to load dashboard data'
      }
    },

    async loadTransactions() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/satmachineclient/api/v1/dashboard/transactions?limit=50',
          this.g.user.wallets[0].inkey
        )

        // Debug: Log the first transaction to see date format
        if (data.length > 0) {
          console.log('Sample transaction data:', data[0])
          console.log('transaction_time:', data[0].transaction_time)
          console.log('created_at:', data[0].created_at)
        }

        // Sort by most recent first and store
        this.transactions = data.sort((a, b) => {
          const dateA = new Date(a.transaction_time || a.created_at)
          const dateB = new Date(b.transaction_time || b.created_at)
          return dateB - dateA  // Most recent first
        })
      } catch (error) {
        console.error('Error loading transactions:', error)
        this.$q.notify({
          type: 'negative',
          message: 'Failed to load transactions',
          position: 'top'
        })
      }
    },

    async refreshAllData() {
      try {
        this.loading = true
        await Promise.all([
          this.loadDashboardData(),
          this.loadTransactions()
        ])
        this.$q.notify({
          type: 'positive',
          message: 'Dashboard refreshed!',
          icon: 'refresh',
          position: 'top'
        })
      } catch (error) {
        console.error('Error refreshing data:', error)
        this.$q.notify({
          type: 'negative',
          message: 'Failed to refresh data',
          position: 'top'
        })
      } finally {
        this.loading = false
      }
    },

    getNextMilestone() {
      if (!this.dashboardData) return { target: 100000, name: '100k sats' }
      const sats = this.dashboardData.total_sats_accumulated

      if (sats < 10000) return { target: 10000, name: '10k sats' }
      if (sats < 100000) return { target: 100000, name: '100k sats' }
      if (sats < 500000) return { target: 500000, name: '500k sats' }
      if (sats < 1000000) return { target: 1000000, name: '1M sats' }
      if (sats < 2100000) return { target: 2100000, name: '2.1M sats' }
      return { target: 21000000, name: '21M sats' }
    },

    getMilestoneProgress() {
      if (!this.dashboardData) return 0
      const sats = this.dashboardData.total_sats_accumulated
      const milestone = this.getNextMilestone()

      // Show total progress toward the next milestone (from 0)
      const progress = (sats / milestone.target) * 100
      return Math.min(Math.max(progress, 0), 100)
    },
    async loadChartData() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          `/satmachineclient/api/v1/dashboard/analytics?time_range=${this.chartTimeRange}`,
          this.g.user.wallets[0].inkey
        )

        // Debug: Log analytics data
        console.log('Analytics data received:', data)
        if (data && data.cost_basis_history && data.cost_basis_history.length > 0) {
          console.log('Sample cost basis point:', data.cost_basis_history[0])
        }

        this.analyticsData = data
        // Use nextTick to ensure DOM is ready
        this.$nextTick(() => {
          this.initDCAChart()
        })
      } catch (error) {
        console.error('Error loading chart data:', error)
      }
    },

    initDCAChart() {
      console.log('initDCAChart called')
      console.log('analyticsData:', this.analyticsData)
      console.log('dcaChart ref:', this.$refs.dcaChart)

      if (!this.analyticsData) {
        console.log('No analytics data available')
        return
      }

      if (!this.$refs.dcaChart) {
        console.log('No chart ref available')
        return
      }

      // Check if Chart.js is loaded
      if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded')
        return
      }

      // Destroy existing chart
      if (this.dcaChart) {
        this.dcaChart.destroy()
      }

      const ctx = this.$refs.dcaChart.getContext('2d')

      // Use accumulation_timeline data which is already aggregated by day
      const timelineData = this.analyticsData.accumulation_timeline || []

      console.log('Timeline data:', timelineData)
      console.log('Timeline data length:', timelineData.length)

      if (timelineData.length === 0) {
        console.log('No timeline data available, falling back to cost basis data')
        // Fallback to cost_basis_history if no timeline data
        const costBasisData = this.analyticsData.cost_basis_history || []
        if (costBasisData.length === 0) {
          console.log('No chart data available')
          // Create gradient for placeholder chart
          const placeholderGradient = ctx.createLinearGradient(0, 0, 0, 300)
          placeholderGradient.addColorStop(0, 'rgba(255, 149, 0, 0.3)')
          placeholderGradient.addColorStop(1, 'rgba(255, 149, 0, 0.05)')
          
          // Show placeholder chart
          this.dcaChart = new Chart(ctx, {
            type: 'line',
            data: {
              labels: ['Start Your DCA Journey'],
              datasets: [{
                label: 'Total Sats Accumulated',
                data: [0],
                borderColor: '#FF9500',
                backgroundColor: placeholderGradient,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 8,
                pointBackgroundColor: '#FFFFFF',
                pointBorderColor: '#FF9500',
                pointBorderWidth: 3
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  titleColor: '#FFFFFF',
                  bodyColor: '#FFFFFF',
                  borderColor: '#FF9500',
                  borderWidth: 2,
                  cornerRadius: 8
                }
              },
              scales: {
                x: {
                  grid: { display: false },
                  ticks: {
                    color: '#666666',
                    font: { size: 12, weight: '500' }
                  }
                },
                y: {
                  beginAtZero: true,
                  grid: {
                    color: 'rgba(255, 149, 0, 0.1)',
                    drawBorder: false
                  },
                  ticks: {
                    color: '#666666',
                    font: { size: 12, weight: '500' },
                    callback: function(value) {
                      return value.toLocaleString() + ' sats'
                    }
                  }
                }
              }
            }
          })
          return
        }

        // Group cost basis data by date to avoid duplicates
        const groupedData = new Map()
        costBasisData.forEach(point => {
          const dateStr = new Date(point.date).toDateString()
          if (!groupedData.has(dateStr)) {
            groupedData.set(dateStr, point)
          } else {
            // Use the latest cumulative values for the same date
            const existing = groupedData.get(dateStr)
            if (point.cumulative_sats > existing.cumulative_sats) {
              groupedData.set(dateStr, point)
            }
          }
        })

        const chartData = Array.from(groupedData.values()).sort((a, b) =>
          new Date(a.date).getTime() - new Date(b.date).getTime()
        )

        const labels = chartData.map(point => {
          // Handle different date formats with improved validation
          let date;
          if (point.date) {
            date = new Date(point.date);
            // Check if date is valid
            if (isNaN(date.getTime())) {
              date = new Date();
            }
          } else {
            date = new Date();
          }
          return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
          })
        })
        const cumulativeSats = chartData.map(point => point.cumulative_sats)

        this.createChart(labels, cumulativeSats)
        return
      }

      // Calculate running totals for timeline data
      let runningSats = 0
      const labels = []
      const cumulativeSats = []

      timelineData.forEach(point => {
        runningSats += point.sats

        const date = new Date(point.date)
        if (!isNaN(date.getTime())) {
          labels.push(date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
          }))
          cumulativeSats.push(runningSats)
        }
      })

      this.createChart(labels, cumulativeSats)
    },

    createChart(labels, cumulativeSats) {
      const ctx = this.$refs.dcaChart.getContext('2d')
      
      // Create gradient for the area fill
      const gradient = ctx.createLinearGradient(0, 0, 0, 300)
      gradient.addColorStop(0, 'rgba(255, 149, 0, 0.4)')
      gradient.addColorStop(0.5, 'rgba(255, 149, 0, 0.2)')
      gradient.addColorStop(1, 'rgba(255, 149, 0, 0.05)')
      
      this.dcaChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Total Sats Accumulated',
            data: cumulativeSats,
            borderColor: '#FF9500',
            backgroundColor: gradient,
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#FFFFFF',
            pointBorderColor: '#FF9500',
            pointBorderWidth: 3,
            pointRadius: 6,
            pointHoverRadius: 8,
            pointHoverBackgroundColor: '#FFFFFF',
            pointHoverBorderColor: '#FF7700',
            pointHoverBorderWidth: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleColor: '#FFFFFF',
              bodyColor: '#FFFFFF',
              borderColor: '#FF9500',
              borderWidth: 2,
              cornerRadius: 8,
              displayColors: false,
              callbacks: {
                title: function(context) {
                  return `📅 ${context[0].label}`
                },
                label: function (context) {
                  return `⚡ ${context.parsed.y.toLocaleString()} sats accumulated`
                }
              }
            }
          },
          scales: {
            x: {
              display: true,
              grid: {
                display: false
              },
              ticks: {
                color: '#666666',
                font: {
                  size: 12,
                  weight: '500'
                }
              }
            },
            y: {
              display: true,
              beginAtZero: true,
              grid: {
                color: 'rgba(255, 149, 0, 0.1)',
                drawBorder: false
              },
              ticks: {
                color: '#666666',
                font: {
                  size: 12,
                  weight: '500'
                },
                callback: function (value) {
                  if (value >= 1000000) {
                    return (value / 1000000).toFixed(1) + 'M sats'
                  } else if (value >= 1000) {
                    return (value / 1000).toFixed(0) + 'k sats'
                  }
                  return value.toLocaleString() + ' sats'
                }
              }
            }
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          },
          elements: {
            point: {
              hoverRadius: 8
            }
          }
        }
      })
    }
  },

  async created() {
    try {
      this.loading = true
      await Promise.all([
        this.loadDashboardData(),
        this.loadTransactions(),
        this.loadChartData()
      ])
    } catch (error) {
      console.error('Error initializing dashboard:', error)
      this.error = 'Failed to initialize dashboard'
    } finally {
      this.loading = false
    }
  },

  mounted() {
    // Initialize chart after DOM is ready
    this.$nextTick(() => {
      if (this.analyticsData) {
        this.initDCAChart()
      }
    })
  },

  computed: {
    hasData() {
      return this.dashboardData && !this.loading
    }
  }
})
