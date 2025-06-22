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
          format: val => val,
          sortable: true,
          sort: (a, b, rowA, rowB) => {
            // Sort by most recent first
            const dateA = new Date(rowA.transaction_time || rowA.created_at);
            const dateB = new Date(rowB.transaction_time || rowB.created_at);
            return dateB - dateA;
          }
        },
        {
          name: 'amount_sats',
          label: 'Bitcoin',
          align: 'right',
          field: 'amount_sats',
          sortable: true
        },
        {
          name: 'amount_fiat',
          label: 'Fiat Amount',
          align: 'right',
          field: 'amount_fiat',
          sortable: true
        },
        {
          name: 'type',
          label: 'Type',
          align: 'center',
          field: 'transaction_type',
          sortable: true
        },
        {
          name: 'status',
          label: 'Status',
          align: 'center',
          field: 'status',
          sortable: true
        }
      ],
      transactionPagination: {
        sortBy: 'date',
        descending: true,
        page: 1,
        rowsPerPage: 10
      }
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
      return new Date(dateString).toLocaleDateString()
    },

    formatTime(dateString) {
      if (!dateString) return ''
      return new Date(dateString).toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    },

    formatSats(amount) {
      if (!amount) return '0 sats'
      return new Intl.NumberFormat('en-US').format(amount) + ' sats'
    },

    async loadDashboardData() {
      try {
        const {data} = await LNbits.api.request(
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
        const {data} = await LNbits.api.request(
          'GET',
          '/satmachineclient/api/v1/dashboard/transactions?limit=50',
          this.g.user.wallets[0].inkey
        )
        // Sort transactions by most recent first
        this.transactions = data.sort((a, b) => {
          const dateA = new Date(a.transaction_time || a.created_at)
          const dateB = new Date(b.transaction_time || b.created_at)
          return dateB - dateA
        })
      } catch (error) {
        console.error('Error loading transactions:', error)
      }
    }
  },

  async created() {
    try {
      this.loading = true
      await Promise.all([
        this.loadDashboardData(),
        this.loadTransactions()
      ])
    } catch (error) {
      console.error('Error initializing dashboard:', error)
      this.error = 'Failed to initialize dashboard'
    } finally {
      this.loading = false
    }
  },

  computed: {
    hasData() {
      return this.dashboardData && !this.loading
    }
  }
})
