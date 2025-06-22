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

  type state_type is (STATE_0, STATE_1, STATE_2, STATE_3);
  signal state : state_type := STATE_0;

  signal tx_dv      : std_logic := '0';
  signal tx_byte    : std_logic_vector(7 downto 0) := x"00";
  signal tx_done    : std_logic;
  signal tx_active  : std_logic;

  signal interbyte_counter : integer range 0 to 2500 := 0;
  
  signal adc_ch0 : std_logic_vector(11 downto 0);
  signal adc_data_latched : std_logic_vector(11 downto 0);
  
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

begin

  -- Show ADC data on LEDs (top 8 bits of 12-bit ADC, similar to Verilog [11:2] but adjusted for 8 LEDs)
  LEDR <= adc_ch0(11 downto 4);
  
  U_ADC : ADC
    port map (
      CLOCK => CLK_50,
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

  -- Byte splitting logic (same as Verilog)
  tx_high <= adc_data_latched(11 downto 4);
  tx_low  <= adc_data_latched(3 downto 0) & "0000";

  process(CLK_50)
  begin
    if rising_edge(CLK_50) then
      if RESET = '0' then
        state         <= STATE_0;
        tx_dv         <= '0';
        tx_byte       <= x"00";
        interbyte_counter <= 0;
      else
        case state is
          when STATE_0 =>
            if tx_active = '0' then
              adc_data_latched <= adc_ch0;  -- Latch current ADC data
              tx_byte <= tx_high;           -- Prepare high byte
              tx_dv <= '1';
              state <= STATE_1;
            end if;

          when STATE_1 =>
            tx_dv <= '0';
            if tx_done = '1' then
              tx_byte <= tx_low;  -- Prepare low byte
              tx_dv <= '1';
              state <= STATE_2;
            end if;

          when STATE_2 =>
            tx_dv <= '0';
            if tx_done = '1' then
              state <= STATE_3;
            end if;

          when STATE_3 =>
            if interbyte_counter < 2500 then  -- ~50 us at 50MHz (matches Verilog timing)
              interbyte_counter <= interbyte_counter + 1;
            else
              interbyte_counter <= 0;
              state <= STATE_0;
            end if;

          when others =>  -- safety fallback
            state <= STATE_0;
        end case;
      end if;
    end if;
  end process;
end RTL;