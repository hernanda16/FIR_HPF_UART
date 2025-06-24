library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity FIR_HPF_UART is
  port (
    CLK_50     : in  std_logic;
    RESET      : in  std_logic;
    LEDR       : out std_logic_vector(7 downto 0);
    UART_OUT   : out std_logic
  );
end FIR_HPF_UART;

architecture RTL of FIR_HPF_UART is
  constant CLKS_PER_BIT : integer := 100;

  constant SAMPLE_CLOCK_DIV : integer := 2500;
  signal sample_clock_counter : integer range 0 to SAMPLE_CLOCK_DIV-1 := 0;
  signal sample_enable : std_logic := '0';
  signal adc_clk : std_logic := '0';

  type state_type is (STATE_0, STATE_1, STATE_2, STATE_3);
  signal state : state_type := STATE_0;

  signal tx_dv      : std_logic := '0';
  signal tx_byte    : std_logic_vector(7 downto 0) := x"00";
  signal tx_done    : std_logic;
  signal tx_active  : std_logic;

  signal interbyte_counter : integer range 0 to 2500 := 0;
  
  signal adc_ch0 : std_logic_vector(11 downto 0);
  signal adc_filtered : std_logic_vector(11 downto 0);
  signal adc_ch0_sampled : std_logic_vector(11 downto 0);
  signal adc_filtered_sampled : std_logic_vector(11 downto 0);
  
  -- Derived signals for high and low bytes
  signal tx_high : std_logic_vector(7 downto 0);
  signal tx_low  : std_logic_vector(7 downto 0);
  
  component ADC
    port (
      CLOCK : in std_logic;
      CH0   : out std_logic_vector(11 downto 0);
      CH1   : out std_logic_vector(11 downto 0);
      CH2   : out std_logic_vector(11 downto 0);
      CH3   : out std_logic_vector(11 downto 0);
      CH4   : out std_logic_vector(11 downto 0);
      CH5   : out std_logic_vector(11 downto 0);
      CH6   : out std_logic_vector(11 downto 0);
      CH7   : out std_logic_vector(11 downto 0);
      RESET : in std_logic	
    );
  end component;

  component UART_TX
    generic (
      g_CLKS_PER_BIT : integer
    );
    port (
      i_Clk       : in  std_logic;
      i_Tx_DV     : in  std_logic;
      i_Tx_Byte   : in  std_logic_vector(7 downto 0);
      o_Tx_Active : out std_logic;
      o_Tx_Serial : out std_logic;
      o_Tx_Done   : out std_logic
    );
  end component;

  component FIR_HPF
    port (
      CLK_50     : in  std_logic;
      INPUT_ADC  : in  std_logic_vector(11 downto 0);
      OUTPUT_ADC : out std_logic_vector(11 downto 0)
    );
  end component;

  component FRAMING
    port (
      CLOCK     : in  std_logic;
      RESET     : in  std_logic;
      DATA0     : in  std_logic_vector(11 downto 0);
      DATA1     : in  std_logic_vector(11 downto 0);
      TX_DV     : out std_logic;
      TX_BYTE   : out std_logic_vector(7 downto 0);
      TX_DONE   : in  std_logic;
      TX_ACTIVE : in  std_logic
    );
  end component;

begin

  -- Show ADC data on LEDs (top 8 bits of 12-bit ADC)
  LEDR <= adc_ch0_sampled(11 downto 4);
  
  U_ADC : ADC
    port map (
      CLOCK => CLK_50,        -- Gunakan clock 50 MHz langsung
      CH0   => adc_ch0,
      CH1   => open,
      CH2   => open,
      CH3   => open,
      CH4   => open,
      CH5   => open,
      CH6   => open,
      CH7   => open,
      RESET => not RESET
    );

  U_UART_TX : UART_TX
    generic map (
      g_CLKS_PER_BIT => CLKS_PER_BIT
    )
    port map (
      i_Clk     => CLK_50,
      i_Tx_DV     => tx_dv,
      i_Tx_Byte   => tx_byte,
      o_Tx_Active => tx_active,
      o_Tx_Serial => UART_OUT,
      o_Tx_Done   => tx_done
    );

  U_FIR_HPF : FIR_HPF
    port map (
      CLK_50 => adc_clk,       -- FIR tetap menggunakan 50 MHz
      INPUT_ADC => adc_ch0, 
      OUTPUT_ADC => adc_filtered 
    );

  U_FRAMING : FRAMING
    port map (
      CLOCK     => CLK_50,
      RESET     => RESET,
      DATA0     => adc_ch0_sampled,     -- Gunakan data yang sudah di-sample
      DATA1     => adc_filtered_sampled, -- Gunakan data filtered yang sudah di-sample
      TX_DV     => tx_dv,
      TX_BYTE   => tx_byte,
      TX_DONE   => tx_done,
      TX_ACTIVE => tx_active
    );

  -- Clock divider process untuk menghasilkan sample enable 20 kHz
  process(CLK_50)
  begin
    if rising_edge(CLK_50) then
      if RESET = '0' then
        sample_clock_counter <= 0;
        sample_enable <= '0';
        adc_clk <= '0';
      else
        if sample_clock_counter = SAMPLE_CLOCK_DIV-1 then
          sample_clock_counter <= 0;
          sample_enable <= '1';  -- Generate pulse setiap 2500 clock cycles (20 kHz)
          adc_clk <= not adc_clk;  -- Toggle adc_clk to create 20kHz clock
        else
          sample_clock_counter <= sample_clock_counter + 1;
          sample_enable <= '0';
        end if;
      end if;
    end if;
  end process;

  -- Sampling process untuk capture data pada 20 kHz rate
  process(CLK_50)
  begin
    if rising_edge(CLK_50) then
      if RESET = '0' then
        adc_ch0_sampled <= (others => '0');
        adc_filtered_sampled <= (others => '0');
      else
        if sample_enable = '1' then
          adc_ch0_sampled <= adc_ch0;           -- Sample raw ADC data
          adc_filtered_sampled <= adc_filtered; -- Sample filtered data
        end if;
      end if;
    end if;
  end process;

end RTL;