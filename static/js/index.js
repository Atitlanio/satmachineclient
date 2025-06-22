window.app = Vue.createApp({
  el: '#dcaClient',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
      dashboardData: null,
      transactions: [],
      loading: true,
      error: null
    }
  },

  methods: {
    formatCurrency(amount) {
      if (!amount) return 'Q 0.00';
      // Convert centavos to quetzales
      return new Intl.NumberFormat('es-GT', {
        style: 'currency',
        currency: 'GTQ',
      }).format(amount / 100);
    },

    formatDate(dateString) {
      if (!dateString) return ''
      return new Date(dateString).toLocaleDateString()
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
          '/satmachineclient/api/v1/dashboard/transactions?limit=10',
          this.g.user.wallets[0].inkey
        )
        this.transactions = data
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
