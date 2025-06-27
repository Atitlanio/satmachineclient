window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
      // Registration state
      isRegistered: false,
      registrationChecked: false,
      showRegistrationDialog: false,
      registrationForm: {
        selectedWallet: null,
        dca_mode: 'flow',
        fixed_mode_daily_limit: null,
        username: ''
      },

      // Dashboard state
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
      analyticsData: null,
      chartLoading: false
    }
  },

  methods: {
    // Registration Methods
    async checkRegistrationStatus() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/satmachineclient/api/v1/registration-status',
          this.g.user.wallets[0].adminkey
        )

        this.isRegistered = data.is_registered
        this.registrationChecked = true

        if (!this.isRegistered) {
          this.showRegistrationDialog = true
          // Pre-fill username and default wallet if available
          this.registrationForm.username = this.g.user.username || ''
          this.registrationForm.selectedWallet = this.g.user.wallets[0]?.id || null
        }

        return data
      } catch (error) {
        console.error('Error checking registration status:', error)
        this.error = 'Failed to check registration status'
        this.registrationChecked = true
      }
    },

    async registerClient() {
      try {
        // Prepare registration data similar to the admin test client creation
        const registrationData = {
          dca_mode: this.registrationForm.dca_mode,
          fixed_mode_daily_limit: this.registrationForm.fixed_mode_daily_limit,
          username: this.registrationForm.username || this.g.user.username || `user_${this.g.user.id.substring(0, 8)}`
        }

        // Find the selected wallet object to get the adminkey
        const selectedWallet = this.g.user.wallets.find(w => w.id === this.registrationForm.selectedWallet)
        if (!selectedWallet) {
          throw new Error('Selected wallet not found')
        }

        const { data } = await LNbits.api.request(
          'POST',
          '/satmachineclient/api/v1/register',
          selectedWallet.adminkey,
          registrationData
        )

        this.isRegistered = true
        this.showRegistrationDialog = false

        this.$q.notify({
          type: 'positive',
          message: data.message || 'Successfully registered for DCA!',
          icon: 'check_circle',
          position: 'top'
        })

        // Load dashboard data after successful registration
        await this.loadDashboardData()

      } catch (error) {
        console.error('Error registering client:', error)
        this.$q.notify({
          type: 'negative',
          message: error.detail || 'Failed to register for DCA',
          position: 'top'
        })
      }
    },

    // Dashboard Methods
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
      if (amount >= 100000000) return formatted + ' sats 🏆' // Full coiner (1 BTC)
      if (amount >= 20000000) return formatted + ' sats 👑' // Bitcoin royalty
      if (amount >= 5000000) return formatted + ' sats 🌟' // Rising star
      if (amount >= 1000000) return formatted + ' sats 💎' // Diamond hands
      if (amount >= 100000) return formatted + ' sats 🚀' // Rocket fuel
      if (amount >= 10000) return formatted + ' sats ⚡' // Lightning
      return formatted + ' sats'
    },

    async loadDashboardData() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/satmachineclient/api/v1/dashboard/summary',
          this.g.user.wallets[0].adminkey
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
          this.g.user.wallets[0].adminkey
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
      if (sats < 5000000) return { target: 5000000, name: '5M sats' }
      if (sats < 20000000) return { target: 20000000, name: '20M sats' }
      if (sats < 100000000) return { target: 100000000, name: '100M sats (1 BTC!)' }
      return { target: 210000000, name: '210M sats (2.1 BTC)' }
    },

    getMilestoneProgress() {
      if (!this.dashboardData) {
        console.log('getMilestoneProgress: no dashboard data')
        return 0
      }
      const sats = this.dashboardData.total_sats_accumulated
      const milestone = this.getNextMilestone()

      // Show total progress toward the next milestone (from 0)
      const progress = (sats / milestone.target) * 100
      const result = Math.min(Math.max(progress, 0), 100)
      console.log('getMilestoneProgress:', { sats, milestone, progress, result })
      return result
    },
    async loadChartData() {
      // Prevent multiple simultaneous requests
      if (this.chartLoading) {
        console.log('Chart already loading, ignoring request')
        return
      }

      try {
        this.chartLoading = true

        // Destroy existing chart immediately to prevent conflicts
        if (this.dcaChart) {
          console.log('Destroying existing chart before loading new data')
          this.dcaChart.destroy()
          this.dcaChart = null
        }

        const { data } = await LNbits.api.request(
          'GET',
          `/satmachineclient/api/v1/dashboard/analytics?time_range=${this.chartTimeRange}`,
          this.g.user.wallets[0].adminkey
        )

        // Debug: Log analytics data
        console.log('Analytics data received:', data)
        if (data && data.cost_basis_history && data.cost_basis_history.length > 0) {
          console.log('Sample cost basis point:', data.cost_basis_history[0])
        }

        this.analyticsData = data

        // Wait for DOM update and ensure we're still in loading state
        await this.$nextTick()

        // Double-check we're still the active loading request
        if (this.chartLoading) {
          this.initDCAChart()
        } else {
          console.log('Chart loading was cancelled, skipping initialization')
          this.chartLoading = false
        }
      } catch (error) {
        console.error('Error loading chart data:', error)
        this.chartLoading = false
      }
    },

    initDCAChart() {
      console.log('initDCAChart called')
      console.log('analyticsData:', this.analyticsData)
      console.log('dcaChart ref:', this.$refs.dcaChart)
      console.log('chartLoading state:', this.chartLoading)

      // Skip if we're not in a loading state (indicates this is a stale call)
      if (!this.chartLoading && this.dcaChart) {
        console.log('Chart already exists and not loading, skipping initialization')
        return
      }

      if (!this.analyticsData) {
        console.log('No analytics data available')
        return
      }

      if (!this.$refs.dcaChart) {
        console.log('No chart ref available, waiting for DOM...')
        // Try again after DOM update, but only if still loading
        this.$nextTick(() => {
          if (this.$refs.dcaChart && this.chartLoading) {
            this.initDCAChart()
          }
        })
        return
      }

      // Check if Chart.js is loaded
      if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded')
        return
      }

      console.log('Chart.js version:', Chart.version || 'unknown')
      console.log('Chart.js available:', typeof Chart)

      // Destroy existing chart (redundant safety check)
      if (this.dcaChart) {
        console.log('Destroying existing chart in initDCAChart')
        this.dcaChart.destroy()
        this.dcaChart = null
      }

      const ctx = this.$refs.dcaChart.getContext('2d')

      // Use accumulation_timeline data which is already grouped by day
      const timelineData = this.analyticsData.accumulation_timeline || []
      console.log('Timeline data sample:', timelineData.slice(0, 2)) // Debug first 2 records

      // If we have timeline data, use it (already grouped by day)
      if (timelineData.length > 0) {
        // Calculate running totals from daily data
        let runningSats = 0
        const labels = []
        const cumulativeSats = []

        timelineData.forEach(point => {
          // Ensure sats is a valid number
          const sats = point.sats || 0
          const validSats = typeof sats === 'number' ? sats : parseFloat(sats) || 0
          runningSats += validSats

          const date = new Date(point.date)
          if (!isNaN(date.getTime())) {
            labels.push(date.toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric'
            }))
            cumulativeSats.push(runningSats)
          }
        })

        console.log('Timeline chart data:', { labels, cumulativeSats })

        this.createChart(labels, cumulativeSats)
        return
      }

      // Fallback to cost_basis_history but group by date to avoid duplicates
      console.log('No timeline data, using cost_basis_history as fallback')
      const chartData = this.analyticsData.cost_basis_history || []
      console.log('Chart data sample:', chartData.slice(0, 2)) // Debug first 2 records

      // Handle empty data case
      if (chartData.length === 0) {
        console.log('No chart data available')
        // Create gradient for placeholder chart
        const placeholderGradient = ctx.createLinearGradient(0, 0, 0, 300)
        placeholderGradient.addColorStop(0, 'rgba(255, 149, 0, 0.3)')
        placeholderGradient.addColorStop(1, 'rgba(255, 149, 0, 0.05)')

        // Show placeholder chart with enhanced styling
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
              pointBorderWidth: 3,
              pointHoverRadius: 10
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
                cornerRadius: 8,
                callbacks: {
                  label: function (context) {
                    return `${context.parsed.y.toLocaleString()} sats`
                  }
                }
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
                  callback: function (value) {
                    return value.toLocaleString() + ' sats'
                  }
                }
              }
            }
          }
        })
        // Clear loading state after creating placeholder chart
        this.chartLoading = false
        return
      }

      // Group cost_basis_history by date to eliminate duplicates
      const groupedData = new Map()
      chartData.forEach(point => {
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

      const uniqueChartData = Array.from(groupedData.values()).sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )

      const labels = uniqueChartData.map(point => {
        // Handle different date formats with enhanced timezone handling
        let date;
        if (point.date) {
          console.log('Raw date from API:', point.date); // Debug the actual date string

          // If it's an ISO string with timezone info, parse it correctly
          if (typeof point.date === 'string' && point.date.includes('T')) {
            // ISO string - parse and convert to local date
            date = new Date(point.date);
            // For display purposes, use the date part only to avoid timezone shifts
            const localDateStr = date.getFullYear() + '-' +
              String(date.getMonth() + 1).padStart(2, '0') + '-' +
              String(date.getDate()).padStart(2, '0');
            date = new Date(localDateStr + 'T00:00:00'); // Force local midnight
          } else {
            date = new Date(point.date);
          }

          // Check if date is valid
          if (isNaN(date.getTime())) {
            date = new Date();
          }
        } else {
          date = new Date();
        }

        console.log('Formatted date:', date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));

        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric'
        })
      })
      const cumulativeSats = uniqueChartData.map(point => {
        // Ensure cumulative_sats is a valid number
        const sats = point.cumulative_sats || 0
        return typeof sats === 'number' ? sats : parseFloat(sats) || 0
      })

      console.log('Final chart data:', { labels, cumulativeSats })
      console.log('Labels array:', labels)
      console.log('CumulativeSats array:', cumulativeSats)

      // Validate data before creating chart
      if (labels.length === 0 || cumulativeSats.length === 0) {
        console.warn('No valid data for chart, skipping creation')
        return
      }

      if (labels.length !== cumulativeSats.length) {
        console.warn('Mismatched data arrays:', { labelsLength: labels.length, dataLength: cumulativeSats.length })
        return
      }

      // Check for any invalid values in cumulativeSats
      const hasInvalidValues = cumulativeSats.some(val => val === null || val === undefined || isNaN(val))
      if (hasInvalidValues) {
        console.warn('Invalid values found in cumulative sats:', cumulativeSats)
        return
      }

      this.createChart(labels, cumulativeSats)
    },

    createChart(labels, cumulativeSats) {
      console.log('createChart called with loading state:', this.chartLoading)

      if (!this.$refs.dcaChart) {
        console.log('Chart ref not available for createChart')
        return
      }

      // Skip if we're not in a loading state (indicates this is a stale call)
      if (!this.chartLoading) {
        console.log('Not in loading state, skipping createChart')
        return
      }

      // Destroy existing chart
      if (this.dcaChart) {
        console.log('Destroying existing chart in createChart')
        this.dcaChart.destroy()
        this.dcaChart = null
      }

      const ctx = this.$refs.dcaChart.getContext('2d')

      try {
        // Create gradient for the area fill
        const gradient = ctx.createLinearGradient(0, 0, 0, 300)
        gradient.addColorStop(0, 'rgba(255, 149, 0, 0.4)')
        gradient.addColorStop(0.5, 'rgba(255, 149, 0, 0.2)')
        gradient.addColorStop(1, 'rgba(255, 149, 0, 0.05)')

        // Small delay to ensure Chart.js is fully initialized
        setTimeout(() => {
          try {
            // Final check to ensure we're still in the correct loading state
            if (!this.chartLoading) {
              console.log('Loading state changed during timeout, aborting chart creation')
              return
            }

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
                      title: function (context) {
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
            console.log('Chart created successfully in createChart!')
            // Chart is now created, clear loading state
            this.chartLoading = false
          } catch (error) {
            console.error('Error in createChart setTimeout:', error)
            this.chartLoading = false
          }
        }, 50)
      } catch (error) {
        console.error('Error creating Chart.js chart in createChart:', error)
        console.log('Chart data that failed:', { labels, cumulativeSats })
        // Clear loading state on error
        this.chartLoading = false
      }
    }
  },

  async created() {
    try {
      this.loading = true

      // Check registration status first
      await this.checkRegistrationStatus()

      // Only load dashboard data if registered
      if (this.isRegistered) {
        await Promise.all([
          this.loadDashboardData(),
          this.loadTransactions(),
          this.loadChartData()
        ])
      }
    } catch (error) {
      console.error('Error initializing dashboard:', error)
      this.error = 'Failed to initialize dashboard'
    } finally {
      this.loading = false
    }
  },

  mounted() {
    // Initialize chart after DOM is ready and data is loaded
    this.$nextTick(() => {
      console.log('Component mounted, checking for chart initialization')
      console.log('Loading state:', this.loading)
      console.log('Chart ref available:', !!this.$refs.dcaChart)
      console.log('Analytics data available:', !!this.analyticsData)

      if (this.analyticsData && this.$refs.dcaChart) {
        console.log('Initializing chart from mounted hook')
        this.initDCAChart()
      } else {
        console.log('Chart will initialize after data loads')
      }
    })
  },

  computed: {
    hasData() {
      return this.dashboardData && !this.loading && this.isRegistered
    },

    walletOptions() {
      if (!this.g.user?.wallets) return []
      return this.g.user.wallets.map(wallet => ({
        label: `${wallet.name} (${Math.round(wallet.balance_msat / 1000)} sats)`,
        value: wallet.id
      }))
    }
  },

  watch: {
    analyticsData: {
      handler(newData) {
        if (newData && !this.chartLoading && !this.dcaChart) {
          console.log('Analytics data changed and no chart exists, initializing chart...')
          this.$nextTick(() => {
            // Only initialize if we don't have a chart and aren't currently loading
            if (!this.dcaChart && !this.chartLoading) {
              this.chartLoading = true
              this.initDCAChart()
            }
          })
        }
      },
      immediate: false
    }
  }
})
