window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
    }
  },

  ///////////////////////////////////////////////////
  ////////////////METHODS FUNCTIONS//////////////////
  ///////////////////////////////////////////////////

  methods: {
    // Utility Methods
    formatCurrency(amount) {
      if (!amount) return 'Q 0.00';

      return new Intl.NumberFormat('es-GT', {
        style: 'currency',
        currency: 'GTQ',
      }).format(amount);
    },

    formatDate(dateString) {
      if (!dateString) return ''
      return new Date(dateString).toLocaleDateString()
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString('en-US', { hour12: false })
    },

    formatSats(amount) {
      if (!amount) return '0 sats'
      return new Intl.NumberFormat('en-US').format(amount) + ' sats'
    },

  },
  ///////////////////////////////////////////////////
  //////LIFECYCLE FUNCTIONS RUNNING ON PAGE LOAD/////
  ///////////////////////////////////////////////////
  async created() {
    // Load DCA client data
    await Promise.all([
    ])
  },

  computed: {
  }
})
